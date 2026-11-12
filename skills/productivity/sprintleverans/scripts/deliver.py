#!/usr/bin/env python3
"""Check, prepare and deliver a sprintleverans pack through the installed Tengella CLI.

  check      lint every selected order.json against FIELDS.md; no network
  preflight  resolve environment, UTV type, requester, sprint and duplicates into readiness.json
  run        take each selected item to its stage; --dry-run prints the plan without writing
  verify     read back Orders and linked stories; write remote-verification.json and LEVERANS-<N>.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

NARRATIVE = ['purpose', 'customerNeed', 'howIsItSolvedToday', 'whereInSystem', 'whereToSolve',
             'suggestedSolution', 'solution', 'implementationDetails']
# The API accepts Lösning and Implementationsdetaljer once the Order is in sprint.
LATE_FIELDS = {'solution', 'implementationDetails'}
ORDER_FIELDS = {'title', 'note', 'contacts', *NARRATIVE}
STATUS = {'created': 1, 'submitted': 2, 'approved': 5, 'in-sprint': 10, 'developed': 7}
STEPS = [('submit', 2, 'submitted'), ('approve', 5, 'approved'), ('prioritize', 5, 'approved'),
         ('assign-sprint', 10, 'in-sprint')]
STAGE_ORDER = ['created', 'submitted', 'approved', 'in-sprint', 'developed']
URL = re.compile(r'https?://\S+')


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path):
    return json.loads(path.read_text())


def save(path: Path, value) -> None:
    temp = path.with_suffix('.new')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


class Pack:
    def __init__(self, root: Path):
        self.root = root
        self.manifest = load(root / 'manifest.json')

    def items(self, selected_only=True):
        for item in self.manifest['items']:
            if item.get('group') == 'done' and (item.get('selected') or not selected_only):
                yield item, load(self.root / item['directory'] / 'order.json')


# ---------------------------------------------------------------- check

def lint(order: dict, root: Path) -> list[str]:
    """Mechanical FIELDS.md rules; judgement (voice, outcome-first) stays with the reviewer."""
    problems = []
    unknown = set(order) - ORDER_FIELDS - {'images'}
    if unknown:
        problems.append(f'unknown fields: {sorted(unknown)}')
    for field in ('title', 'purpose', 'customerNeed', 'howIsItSolvedToday', 'solution',
                  'implementationDetails', 'note'):
        if not str(order.get(field) or '').strip():
            problems.append(f'{field} is empty')
    if len(order.get('title') or '') > 70:
        problems.append('title is longer than 70 characters')
    solution = order.get('solution') or ''
    if len(solution.split()) > 60:
        problems.append(f'solution has {len(solution.split())} words; the slide allows 60')
    if URL.search(solution) or re.search(r'\bPR\s*\d+', solution):
        problems.append('solution contains a URL or PR reference; move it to implementationDetails')
    note = order.get('note') or ''
    if '\n' in note.strip() or not note.startswith('Sprint '):
        problems.append('note must be one line starting "Sprint <N> · arbete …"')
    for line in (order.get('implementationDetails') or '').splitlines():
        if URL.search(line) and not line.lstrip().startswith('•'):
            problems.append(f'source URL outside a bullet: {line.strip()[:60]}')
    sentences = {}
    for field in NARRATIVE:
        for sentence in re.split(r'(?<=[.!?])\s+|\n+', order.get(field) or ''):
            key = sentence.strip(' •').lower()
            if len(key) > 40:
                if key in sentences and sentences[key] != field:
                    problems.append(f'{field} repeats a sentence from {sentences[key]}')
                sentences.setdefault(key, field)
    for image in order.get('images', []):
        path = root / image['path']
        if image.get('field') not in NARRATIVE:
            problems.append(f"{image['path']}: field must be one of {NARRATIVE}")
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg') or not path.is_file():
            problems.append(f"{image['path']}: missing or not PNG/JPEG")
        if not image.get('alt') or len(image['alt']) > 500:
            problems.append(f"{image['path']}: alt text missing or over 500 characters")
        size = image_size(path) if path.is_file() else None
        # Present draws images about 1200 CSS px wide. Fewer source pixels, or a tall full-page
        # capture that the screenshot tool scaled down to fit, reads as blurry on the projector.
        if size and (size[0] < MIN_IMAGE_WIDTH or size[1] > 1.25 * size[0]):
            problems.append(f"{image['path']}: {size[0]}x{size[1]}; capture a crop at least "
                            f"{MIN_IMAGE_WIDTH} px wide and at most 1.25x as tall as wide")
    return problems


MIN_IMAGE_WIDTH = 1600


def image_size(path: Path) -> tuple[int, int] | None:
    """Width and height from a PNG or baseline/progressive JPEG header."""
    data = path.read_bytes()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
    position = 2
    while data[:2] == b'\xff\xd8' and position + 9 < len(data):
        marker, length = data[position + 1], int.from_bytes(data[position + 2:position + 4], 'big')
        if marker in (0xC0, 0xC1, 0xC2):
            return (int.from_bytes(data[position + 7:position + 9], 'big'),
                    int.from_bytes(data[position + 5:position + 7], 'big'))
        position += 2 + length
    return None


def check(pack: Pack) -> int:
    failures = 0
    for item, order in pack.items(selected_only=False):
        problems = lint(order, pack.root)
        failures += bool(problems)
        print(json.dumps({'item': item['id'], 'ok': not problems, 'problems': problems}, ensure_ascii=False))
    return 1 if failures else 0


# ---------------------------------------------------------------- CLI plumbing

class Cli:
    def __init__(self, pack: Pack, readiness: dict | None, dry_run=False):
        self.pack, self.readiness, self.dry_run = pack, readiness or {}, dry_run
        env = pack.manifest['environment']
        self.target = ['--environment', env] + (['--apphost', self.readiness['apphost']] if self.readiness.get('apphost') else [])
        self.confirm = ['--confirm', 'production'] if env == 'production' else ['--yes']

    def read(self, *args: str) -> dict:
        result = subprocess.run(['tengella', *args, *self.target, '--json'], capture_output=True, text=True)
        document = json.loads(result.stdout)
        if result.returncode or not document.get('success'):
            raise RuntimeError(f"tengella {' '.join(args)}: {document.get('errors')}")
        return document['data']

    def write(self, args: list[str], output: Path) -> tuple[int, dict]:
        command = ['tengella', *args, *self.target, '--expected-environment', self.readiness['fingerprint'],
                   *self.confirm, '--json']
        if self.dry_run:
            print('DRY', shlex.join(command))
            return 0, {}
        with (self.pack.root / 'commands.txt').open('a') as log:
            log.write(shlex.join(command) + '\n')
        result = subprocess.run(command, capture_output=True, text=True)
        try:
            document = json.loads(result.stdout)
        except json.JSONDecodeError:
            document = {'success': False, 'errors': [{'code': 'unparsed', 'message': 'Inspect commands.txt and the CLI log.'}]}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
        return result.returncode, document


# ---------------------------------------------------------------- preflight

def preflight(pack: Pack, apphost: str | None) -> int:
    manifest = pack.manifest
    cli = Cli(pack, {'apphost': apphost})
    status = subprocess.run(['tengella', 'account', 'status', '--json'], capture_output=True, text=True)
    active = json.loads(status.stdout)['data']['activeEnvironment']
    if active['name'] != manifest['environment']:
        # `account status --environment` still reports the active environment; login switches it
        # without a browser when the target session is ready.
        raise SystemExit(f"Active CLI environment is {active['name']}, manifest wants {manifest['environment']}; "
                         f"select it with `tengella account login --provider tengella --environment {manifest['environment']}"
                         f"{' --apphost ' + apphost if apphost else ''} --json`.")
    if apphost and Path(active.get('appHost') or '').resolve() != Path(apphost).resolve():
        raise SystemExit(f"Active AppHost is {active.get('appHost')}; select it with "
                         f"`tengella account login --provider tengella --environment {manifest['environment']} --apphost {apphost} --json`.")
    if 'tengella:operations:order:write' not in (active.get('sessionKey') or ''):
        raise SystemExit('The CLI session lacks Order write scope; sign in again with consent.')
    types = cli.read('order', 'options', '--kind', 'types', '--page-size', '100')['items']
    requesters = cli.read('order', 'options', '--kind', 'requesters', '--page-size', '100')['items']
    utv = [t for t in types if t['label'] == 'UTV']
    requester = [r for r in requesters if r['label'] == manifest['requester']]
    sprint = cli.read('order', 'sprint', 'show', '--sprint', str(manifest['sprint']))
    if len(utv) != 1 or len(requester) != 1 or not sprint.get('exists'):
        raise SystemExit(json.dumps({'utv': utv, 'requester': requester, 'sprint': sprint}, ensure_ascii=False))
    titles = {order['title'].strip().lower(): item['id'] for item, order in pack.items(selected_only=False)}
    duplicates, cursor, checked = [], None, 0
    while True:
        page = cli.read('order', 'list', '--page-size', '100', *(['--after', cursor] if cursor else []))
        for order in page['items']:
            checked += 1
            if order['title'].strip().lower() in titles:
                duplicates.append({'item': titles[order['title'].strip().lower()], 'orderId': order['id'],
                                   'number': order['number'], 'status': order['status']})
        cursor = page.get('nextCursor')
        if not page.get('hasNextPage') or not cursor:
            break
    readiness = {'checkedAt': now(), 'environment': active['name'], 'api': active['api'].rstrip('/') + '/',
                 'fingerprint': active['fingerprint'], 'apphost': apphost, 'utvTypeId': utv[0]['id'],
                 'requesterId': requester[0]['id'], 'sprint': sprint,
                 'duplicates': {'checked': checked, 'matches': duplicates}}
    save(pack.root / 'readiness.json', readiness)
    print(json.dumps({k: readiness[k] for k in ('environment', 'utvTypeId', 'requesterId')} |
                     {'sprint': sprint['iterationPath'], 'duplicates': duplicates}, ensure_ascii=False))
    return 1 if duplicates else 0


# ---------------------------------------------------------------- run

def run(pack: Pack, dry_run: bool) -> int:
    manifest, root = pack.manifest, pack.root
    readiness = load(root / 'readiness.json')
    if not dry_run and not manifest['authorization'].get('orderWrites'):
        raise SystemExit('manifest.authorization.orderWrites is false; record the user\'s instruction first.')
    if readiness['duplicates']['matches']:
        raise SystemExit('readiness.json lists duplicate titles; set existingOrderId or retitle, then rerun preflight.')
    choices = manifest['choices']
    if set(choices) != {'requireCustomerAccept', 'shouldBeInvoiced'} or None in choices.values():
        raise SystemExit('manifest.choices needs explicit requireCustomerAccept and shouldBeInvoiced.')
    cli = Cli(pack, readiness, dry_run)
    ledger_path = root / 'ledger.json'
    ledger = load(ledger_path) if ledger_path.exists() else {'operations': [], 'orders': {}}
    lock = root / '.delivery.lock'
    if not dry_run:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)

    def persist():
        if not dry_run:
            save(ledger_path, ledger)

    def dispatch(item, step, args):
        """Record the operation ID before sending; refuse to resend an uncertain one."""
        key = f"{item['id']}/{step}"
        previous = next((row for row in ledger['operations'] if row['key'] == key), None)
        if previous and previous['state'] == 'verified':
            return load(root / previous['response'])['data']
        if previous:
            raise RuntimeError(f"{key}: operation {previous['operationId']} needs `tengella order operation` "
                               'inspection; deliver.py never resends it with a new ID.')
        operation = str(uuid.uuid4())
        output = root / item['directory'] / 'execution' / f'{step}.json'
        row = {'key': key, 'operationId': operation, 'state': 'dispatching', 'startedAt': now(),
               'response': str(output.relative_to(root))}
        if not dry_run:
            ledger['operations'].append(row)
        persist()
        code, document = cli.write([*args, '--operation-id', operation], output)
        if dry_run:
            return {'orderId': 0, 'number': '0', 'revision': 'REV', 'status': None, 'syncState': 'NotRequired',
                    'operation': {'revision': 'REV', 'state': 'Associated', 'file': {'sha256': ''}}}
        row.update({'exitCode': code, 'finishedAt': now(), 'errors': document.get('errors', []),
                    'state': 'verified' if code == 0 else 'needs-inspection'})
        persist()
        if code:
            raise RuntimeError(f'{key}: exit {code}; operation {operation} retained for inspection.')
        return document['data']

    def effects(data, status):
        if dry_run:
            return {'revision': 'REV', 'workItemId': None, 'syncState': 'NotRequired', 'orderId': 0, 'number': '0'}
        value = data['effects']
        assert data['localState'] == 'confirmed' and data['readbackVerified'] is True, data
        assert value['status'] == status, value
        assert value['syncState'] in ('NotRequired', 'Succeeded'), value
        return value

    try:
        for item, order in pack.items():
            state = ledger['orders'].setdefault(item['id'], {'title': order['title']})
            if state.get('state') == item.get('stage', 'developed'):
                continue
            state.pop('blocker', None)
            folder = root / item['directory']
            target = STAGE_ORDER.index(item.get('stage', 'developed'))
            content = {k: v for k, v in order.items() if k in ORDER_FIELDS}
            try:
                if item.get('existingOrderId'):
                    current = cli.read('order', 'show', '--id', str(item['existingOrderId']))
                    identifier, number, revision = current['id'], current['number'], current['revision']
                    reached = next((s for s, n in STATUS.items() if n == current['statusId']), 'created')
                    done = STAGE_ORDER.index(reached)
                    # Approved and prioritized share a status; the queue position tells them apart.
                    prioritized = reached != 'approved' or current.get('priority') is not None
                    early = {k: v for k, v in content.items() if k not in LATE_FIELDS}
                    file = folder / 'execution' / 'update-early.json'
                    if not dry_run:
                        save(file, {'content': early})
                    revision = effects(dispatch(item, 'update-early', ['order', 'update', '--id', str(identifier),
                                       '--expected-revision', revision, '--fields-file', str(file)]), current['statusId'])['revision']
                    current_status = current['statusId']
                else:
                    creation = {'orderTypeId': readiness['utvTypeId'], 'requesterId': readiness['requesterId'], **choices,
                                'content': {k: v for k, v in content.items() if k not in LATE_FIELDS}}
                    file = folder / 'execution' / 'create-request.json'
                    if not dry_run:
                        file.parent.mkdir(exist_ok=True)
                        save(file, creation)
                    result = effects(dispatch(item, 'create', ['order', 'create', '--fields-file', str(file)]), 1)
                    identifier, number, revision, done = result['orderId'], result['number'], result['revision'], 0
                    prioritized, current_status = False, 1
                state.update({'id': identifier, 'number': number, 'state': STAGE_ORDER[done],
                              'url': f"{readiness['api']}Order/Review?orderId={identifier}"})
                persist()
                for verb, status, stage in STEPS:
                    position = STAGE_ORDER.index(stage)
                    if position > target:
                        break
                    if position < done or (position == done and (verb != 'prioritize' or prioritized)):
                        continue
                    args = ['order', verb, '--id', str(identifier), '--expected-revision', revision]
                    if verb == 'assign-sprint':
                        args += ['--sprint', str(manifest['sprint'])]
                    result = effects(dispatch(item, verb, args), status)
                    current_status = status
                    revision = result['revision']
                    state.update({'state': stage, 'revision': revision, 'workItemId': result.get('workItemId'),
                                  'syncState': result['syncState']})
                    persist()
                if target >= STAGE_ORDER.index('in-sprint'):
                    late = {k: v for k, v in content.items() if k in LATE_FIELDS}
                    file = folder / 'execution' / 'update-late.json'
                    if not dry_run:
                        save(file, {'content': late})
                    revision = effects(dispatch(item, 'update-late', ['order', 'update', '--id', str(identifier),
                                       '--expected-revision', revision, '--fields-file', str(file)]), current_status)['revision']
                    for index, image in enumerate(order.get('images', [])):
                        source = root / image['path']
                        digest = hashlib.sha256(source.read_bytes()).hexdigest().upper()
                        data = dispatch(item, f'image-{index}', ['order', 'file', 'upload', '--id', str(identifier),
                                        '--expected-revision', revision, '--content-file', str(source),
                                        '--field', image['field'], '--alt', image['alt']])
                        if not dry_run:
                            assert data['readbackVerified'] is True and data['operation']['state'] == 'Associated', data
                            assert data['operation']['file']['sha256'].upper() == digest, 'uploaded bytes differ'
                        revision = data['operation']['revision']
                if target == STAGE_ORDER.index('developed') and current_status != STATUS['developed']:
                    result = effects(dispatch(item, 'mark-developed', ['order', 'mark-developed', '--id', str(identifier),
                                     '--expected-revision', revision]), 7)
                    revision = result['revision']
                    state.update({'state': 'developed', 'revision': revision, 'workItemId': result.get('workItemId'),
                                  'syncState': result['syncState'],
                                  'presentationUrl': f"{readiness['api']}Order/Present?orderId={identifier}"})
                persist()
                print(json.dumps({'event': 'reached', 'item': item['id'], 'order': number, 'stage': state['state'],
                                  'url': state.get('presentationUrl', state['url'])}, ensure_ascii=False), flush=True)
            except Exception as error:  # one blocked item never stops the independent ones
                state['blocker'] = str(error)
                persist()
                print(json.dumps({'event': 'blocked', 'item': item['id'], 'reason': str(error)}, ensure_ascii=False), flush=True)
    finally:
        if not dry_run:
            lock.unlink()
    blocked = [k for k, v in ledger['orders'].items() if v.get('blocker')]
    print(json.dumps({'event': 'finished', 'blocked': blocked}))
    return 1 if blocked else 0


# ---------------------------------------------------------------- verify

def verify(pack: Pack) -> int:
    manifest, root = pack.manifest, pack.root
    readiness = load(root / 'readiness.json')
    ledger = load(root / 'ledger.json')
    cli = Cli(pack, readiness)
    rows, problems = [], []
    for item, order in pack.items():
        state = ledger['orders'].get(item['id'], {})
        if 'id' not in state:
            problems.append(f"{item['id']}: no Order in the ledger")
            continue
        final = cli.read('order', 'show', '--id', str(state['id']))
        row = {'item': item['id'], 'orderId': state['id'], 'number': final['number'], 'title': final['title'],
               'status': final.get('status'), 'statusId': final['statusId'], 'sprint': final.get('sprint'),
               'workItemId': final.get('workItemId'), 'workItemUrl': final.get('workItemUrl'),
               'presentationUrl': f"{readiness['api']}Order/Present?orderId={state['id']}"}
        expected = STATUS[item.get('stage', 'developed')]
        if final['statusId'] != expected:
            problems.append(f"{item['id']}: status {final['statusId']}, expected {expected}")
        # The text projection appends each inline image's alt text right after the authored text.
        if not (final['content'].get('solution') or {}).get('text', '').startswith(order['solution'].strip()) and expected in (10, 7):
            problems.append(f"{item['id']}: saved Lösning differs from order.json")
        if final.get('workItemId'):
            story = subprocess.run(['tengella', 'devops', 'item', 'show', str(final['workItemId']), '--json'],
                                   capture_output=True, text=True)
            fields = json.loads(story.stdout)['data']['fields']
            row |= {'storyState': fields['System.State'], 'iteration': fields['System.IterationPath']}
            if expected == 7 and fields['System.State'] != 'Resolved':
                problems.append(f"{item['id']}: story {final['workItemId']} is {fields['System.State']}")
        rows.append(row)
    save(root / 'remote-verification.json', {'verifiedAt': now(), 'items': rows, 'problems': problems})
    lines = [f"# Sprintleverans {manifest['sprint']}", '',
             f"Period {manifest['period']['from']}–{manifest['period']['to']} · {len(rows)} Orders", '',
             '| Order | Titel | Status | Story |', '| --- | --- | --- | --- |']
    for row in rows:
        story = f"[{row['workItemId']}]({row['workItemUrl']})" if row.get('workItemUrl') else '–'
        lines.append(f"| [{row['number']}]({row['presentationUrl']}) | {row['title']} | {row.get('status')} | {story} |")
    wip = [load(root / i['directory'] / 'order.json')['title'] for i in manifest['items'] if i.get('group') == 'wip']
    if wip:
        lines += ['', '## Pågående', ''] + [f'- {title}' for title in wip]
    (root / f"LEVERANS-{manifest['sprint']}.md").write_text('\n'.join(lines) + '\n')
    print(json.dumps({'verified': len(rows), 'problems': problems}, ensure_ascii=False))
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['check', 'preflight', 'run', 'verify'])
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--apphost', help='local AppHost project (preflight, non-production only)')
    parser.add_argument('--dry-run', action='store_true', help='run: print commands without writing')
    args = parser.parse_args()
    os.umask(0o077)
    pack = Pack(args.pack.resolve())
    if args.command == 'check':
        return check(pack)
    if args.command == 'preflight':
        return preflight(pack, args.apphost)
    if args.command == 'run':
        if check(pack):
            print('check failed; fix order.json before delivery', file=sys.stderr)
            return 1
        return run(pack, args.dry_run)
    return verify(pack)


if __name__ == '__main__':
    sys.exit(main())

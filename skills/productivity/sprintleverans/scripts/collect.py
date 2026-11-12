#!/usr/bin/env python3
"""Collect sprint activity leads into <pack>/collect/ without copying message bodies or auth state.

Reads only: completed PRs through `tengella devops pr list`, local Codex and Claude session
files, and screenshot leads. T3 threads need the T3 tools and are read by the agent, not here.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

STOCKHOLM = ZoneInfo('Europe/Stockholm')
EVIDENCE_DIR = Path.home() / '.t3/userdata/sprint-evidence'
SCREENSHOT_DIRS = [EVIDENCE_DIR, Path.home() / '.t3/userdata/browser-artifacts']
PR_URL = re.compile(r'https://dev\.azure\.com/tengella/[^/\s<>)]+/_git/[^/\s<>)]+/pullrequest/\d+')
ISSUE_KEY = re.compile(r'\b(?:DEV|LAB|PRO)-\d+\b')
IMAGE_PATH = re.compile(r'/(?:home/[^/\s]+|tmp)/[^\s<>\])"\']+\.(?:png|jpe?g)', re.IGNORECASE)
TENGELLA_CWD = re.compile(r'/dev/tengella/|/\.t3/worktrees/(?:tengella_bare|cli|kundportalen|nuget|'
                          r'mina-stadtjanster|mobilkvittens|planperform-mobile|portal-next|skills)/')
INJECTED = ('# AGENTS.md', '## Memory', '<environment_context>', '<INSTRUCTIONS>', '<system-reminder>')


def tengella(*args: str) -> dict:
    """Run one CLI command with --json; stdout is a single JSON document."""
    result = subprocess.run(['tengella', *args, '--json'], capture_output=True, text=True)
    document = json.loads(result.stdout)
    if result.returncode or not document.get('success'):
        raise SystemExit(f"tengella {' '.join(args)} failed: {document.get('errors')}")
    return document['data']


def sprint_window(sprint: int, environment: str) -> tuple[date, date]:
    """Sprint start through today: delivery day falls after the sprint's end date."""
    data = tengella('order', 'sprint', 'show', '--sprint', str(sprint), '--environment', environment)
    if not data.get('exists'):
        raise SystemExit(f'Sprint {sprint} does not exist in {environment}.')
    return date.fromisoformat(data['startDate'][:10]), date.today()


def completed_prs(author: str, start: datetime, end: datetime) -> list[dict]:
    """Page the whole project through the CLI's v2 continuation contract."""
    found = []
    args = ['devops', 'pr', 'list', '--author', author, '--status', 'completed',
            '--closed-after', start.isoformat(), '--closed-before', end.isoformat(), '--limit', '100']
    seen = set()
    while True:
        data = tengella(*args)
        for pr in data['pullRequests']:
            repository = pr['repository']
            closed = datetime.fromisoformat(pr['closedDate'].replace('Z', '+00:00'))
            if start <= closed <= end:
                found.append({'id': pr['id'], 'repository': repository, 'title': pr['title'],
                              'url': f"https://dev.azure.com/tengella/{pr['project']}/_git/{repository}/pullrequest/{pr['id']}",
                              'source': pr['sourceRef'], 'target': pr['targetRef'],
                              'created': pr['createdDate'], 'closed': pr['closedDate'],
                              'issueKeys': sorted(set(ISSUE_KEY.findall(pr['title'] + (pr.get('description') or '')))),
                              'description': (pr.get('description') or '')[:2000]})
        if not data['collection'].get('hasMore'):
            return found
        command = data['collection'].get('nextCommand')
        if not command or command in seen:
            raise SystemExit('PR collection hasMore without a new nextCommand; refusing incomplete results.')
        seen.add(command)
        parts = shlex.split(command)
        if parts[:4] != ['tengella', 'devops', 'pr', 'list']:
            raise SystemExit('Unexpected PR continuation command.')
        args = [part for part in parts[1:] if part != '--json']


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(block.get('text', '') for block in content
                         if isinstance(block, dict) and block.get('type') in ('text', 'input_text', 'output_text'))
    return ''


def instant(value) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def sessions(start: datetime, end: datetime) -> list[dict]:
    """Index Codex and Claude sessions by actual message timestamps; keep references only."""
    rows = []
    for provider, root in [('codex', Path.home() / '.codex/sessions'), ('claude', Path.home() / '.claude/projects')]:
        for file in root.rglob('*.jsonl') if root.is_dir() else []:
            if file.stat().st_mtime < start.timestamp():
                continue
            cwd, session_id, subagent = '', file.stem, False
            first = last = None
            humans = 0
            prs, issues, images = set(), set(), set()
            with file.open(errors='replace') as stream:
                for line in stream:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    payload = record.get('payload') or {}
                    if record.get('type') == 'session_meta':
                        cwd = payload.get('cwd', cwd)
                        session_id = payload.get('id', session_id)
                        subagent = 'subagent' in str(payload.get('source', '')).lower()
                    cwd = record.get('cwd', cwd)
                    subagent = subagent or bool(record.get('isSidechain'))
                    stamp = instant(record.get('timestamp'))
                    if stamp is None or not start <= stamp <= end:
                        continue
                    role = text = None
                    if provider == 'codex' and record.get('type') == 'response_item' and payload.get('type') == 'message':
                        role, text = payload.get('role'), text_of(payload.get('content'))
                    elif provider == 'claude' and record.get('type') in ('user', 'assistant'):
                        role, text = record['type'], text_of((record.get('message') or {}).get('content'))
                    if role not in ('user', 'assistant') or not text or text.lstrip().startswith(INJECTED):
                        continue
                    first, last = min(first or stamp, stamp), max(last or stamp, stamp)
                    humans += role == 'user'
                    prs.update(PR_URL.findall(text))
                    issues.update(ISSUE_KEY.findall(text))
                    images.update(p for p in IMAGE_PATH.findall(text) if Path(p).is_file())
            if first and (TENGELLA_CWD.search(cwd) or prs):
                rows.append({'provider': provider, 'sessionId': session_id, 'file': str(file), 'cwd': cwd,
                             'subagent': subagent, 'first': first.isoformat(), 'last': last.isoformat(),
                             'humanMessages': humans, 'prUrls': sorted(prs), 'issueKeys': sorted(issues),
                             'imageLeads': sorted(images)})
    return rows


def screenshots(start: datetime, end: datetime, leads: set[str]) -> list[dict]:
    """Screenshot files from the evidence folders and session leads, dated by modification time."""
    paths = set(leads)
    for folder in SCREENSHOT_DIRS:
        if folder.is_dir():
            paths.update(str(p) for p in folder.rglob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg'))
    rows = []
    for path in sorted(paths):
        file = Path(path)
        modified = datetime.fromtimestamp(file.stat().st_mtime, timezone.utc)
        if start <= modified <= end:
            rows.append({'path': path, 'modified': modified.isoformat(), 'bytes': file.stat().st_size,
                         'fromEvidenceFolder': file.is_relative_to(EVIDENCE_DIR)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--sprint', type=int, required=True)
    parser.add_argument('--environment', default='production')
    parser.add_argument('--from', dest='start', type=date.fromisoformat, help='override the sprint start')
    parser.add_argument('--to', dest='end', type=date.fromisoformat, help='override the end (default today)')
    parser.add_argument('--author', default='me', help='PR creator; default: signed-in account')
    parser.add_argument('--repo', action='append', help='repository in project Tengella; repeatable')
    args = parser.parse_args()

    start_day, end_day = sprint_window(args.sprint, args.environment)
    start_day, end_day = args.start or start_day, args.end or end_day
    start = datetime.combine(start_day, time.min, STOCKHOLM).astimezone(timezone.utc)
    end = min(datetime.combine(end_day + timedelta(days=1), time.min, STOCKHOLM).astimezone(timezone.utc),
              datetime.now(timezone.utc))
    author = args.author

    out = args.pack / 'collect'
    out.mkdir(parents=True, exist_ok=True)
    prs = completed_prs(author, start, end)
    if args.repo:
        prs = [pr for pr in prs if pr['repository'] in args.repo]
    rows = sessions(start, end)
    images = screenshots(start, end, {p for row in rows for p in row['imageLeads']})
    window = {'from': start_day.isoformat(), 'to': end_day.isoformat(), 'startUtc': start.isoformat(), 'endUtc': end.isoformat()}
    for name, items in [('prs', prs), ('sessions', rows), ('images', images)]:
        (out / f'{name}.json').write_text(json.dumps({'window': window, 'items': items}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'window': window, 'prs': len(prs), 'byRepository': {r: sum(p['repository'] == r for p in prs)
                      for r in sorted({p['repository'] for p in prs})}, 'sessions': len(rows),
                      'screenshots': len(images), 'output': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()

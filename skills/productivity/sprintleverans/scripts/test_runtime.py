"""Runtime and pre-write guards; all CLI targets are temporary local stubs."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parent
LAUNCHER = SCRIPTS / 'python.sh'
DELIVER = SCRIPTS / 'deliver.py'
SOLUTION = '**Klart** med länkar & stöd.\n\n- Första punkten\n- Andra punkten'
TEXT = 'Klart med länkar & stöd. Första punkten Andra punkten'


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pack = self.root / 'pack'
        self.order_dir = self.pack / 'orders' / 'one'
        self.order_dir.mkdir(parents=True)
        self.manifest = dict(
            environment='development', sprint=183, period={'from': '2026-11-01', 'to': '2026-11-12'},
            authorization={'orderWrites': True},
            choices={'requireCustomerAccept': False, 'shouldBeInvoiced': False},
            items=[dict(id='one', group='done', selected=True, directory='orders/one', stage='developed')])
        self.order = dict(title='Bevara uppgifter', purpose='Att behålla uppgifter.',
                          customerNeed='Personal förlorade sina uppgifter.',
                          howIsItSolvedToday='De skriver in allt igen.', solution=SOLUTION,
                          implementationDetails='Källor:\n- [PR 42](https://example.invalid/pr/42)',
                          note='Sprint 183 · arbete 1–12 nov 2026')
        self.save_manifest()
        (self.order_dir / 'order.json').write_text(json.dumps(self.order))
        (self.pack / 'readiness.json').write_text(json.dumps(dict(
            duplicates={'matches': []}, fingerprint='fake', utvTypeId=1, requesterId=1,
            api='https://example.invalid/')))
        self.calls = self.root / 'cli-calls'
        self.response = self.root / 'response.json'
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        target = bin_dir / 'tengella'
        # Even unexpected mutations only touch this disposable marker and return a failure.
        target.write_text('#!/bin/bash\n'
                          'printf "%s\\n" "$*" >> "$FAKE_CALLS"\n'
                          'if [[ "$1 $2" != "order show" ]]; then exit 91; fi\n'
                          'cat "$FAKE_RESPONSE"\n')
        target.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{bin_dir}{os.pathsep}{os.environ["PATH"]}',
                        FAKE_CALLS=str(self.calls), FAKE_RESPONSE=str(self.response))

    def save_manifest(self):
        (self.pack / 'manifest.json').write_text(json.dumps(self.manifest))

    def invoke(self, command, *, no_site=False, env=None, launcher=False):
        prefix = ['bash', str(LAUNCHER)] if launcher else [sys.executable, '-I'] + (['-S'] if no_site else [])
        return subprocess.run([*prefix, str(DELIVER), command, '--pack', str(self.pack)],
                              env=env or self.env, cwd=self.root, capture_output=True, text=True, timeout=60)

    def assert_no_delivery(self):
        self.assertFalse(self.calls.exists(), 'No CLI operation may start before runtime readiness')
        self.assertFalse((self.pack / 'ledger.json').exists())
        self.assertFalse((self.pack / '.delivery.lock').exists())
        self.assertFalse((self.order_dir / 'execution').exists())

    def test_direct_python_missing_parser_stops_before_cli_and_ledger(self):
        # -S deliberately removes site-packages, even when this suite has the correct runtime.
        for command, existing in [('preflight', False), ('verify', False), ('run', False), ('run', True)]:
            with self.subTest(command=command, existing=existing):
                if existing:
                    self.manifest['items'][0]['existingOrderId'] = 42
                    self.save_manifest()
                result = self.invoke(command, no_site=True)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('Final verification is not ready', result.stderr)
                self.assertIn('python.sh', result.stderr)
                self.assert_no_delivery()

    def test_missing_transitive_parser_dependency_also_stops_delivery(self):
        # A partially damaged environment must fail before any external operation as well.
        source = f'''
import builtins, runpy, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'mdurl':
        raise ModuleNotFoundError("No module named 'mdurl'")
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
sys.argv = [{str(DELIVER)!r}, 'run', '--pack', {str(self.pack)!r}]
runpy.run_path({str(DELIVER)!r}, run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-c', source], env=self.env,
                                capture_output=True, text=True, timeout=60)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("No module named 'mdurl'", result.stderr)
        self.assertIn('Final verification is not ready', result.stderr)
        self.assert_no_delivery()

    def test_offline_empty_cache_cannot_start_delivery(self):
        # Keep the suite's managed interpreter available but remove all cached packages and venvs.
        env = dict(self.env, UV_CACHE_DIR=str(self.root / 'empty-cache'), UV_OFFLINE='1',
                   UV_PROJECT_ENVIRONMENT=str(self.root / 'empty-venv'), UV_PYTHON_DOWNLOADS='never')
        result = self.invoke('run', env=env, launcher=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Sprintleverans runtime is not ready; no command was started', result.stderr)
        self.assertIn('network access', result.stderr)
        self.assert_no_delivery()

    def test_isolated_runtime_imports_locked_dependencies(self):
        # A hostile cwd/PYTHONPATH must not shadow the parser or standard library.
        for module in ('markdown_it', 'mdurl'):
            (self.root / f'{module}.py').write_text('raise RuntimeError("shadow module loaded")\n')
        source = '''
import importlib.metadata, pathlib, sys, tomllib
import markdown_it, mdurl
assert sys.flags.isolated == 1
assert sys.prefix != sys.base_prefix
lock = tomllib.loads(pathlib.Path(sys.argv[1]).read_text())
for package in lock['package']:
    if package['name'] != 'sprintleverans-runtime':
        assert importlib.metadata.version(package['name']) == package['version']
print('python -I: locked Markdown dependencies imported from virtual environment')
'''
        result = subprocess.run([sys.executable, '-I', '-c', source, str(SCRIPTS.parent / 'uv.lock')],
                                env=dict(self.env, PYTHONPATH=str(self.root)), cwd=self.root,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_verify_with_stubbed_readback_preserves_markdown_comparison(self):
        (self.pack / 'ledger.json').write_text(json.dumps({'orders': {'one': {'id': 42}}}))
        for actual, expected in [(TEXT + ' Bildens alt-text', 0), ('Ändrad lösning', 1)]:
            with self.subTest(actual=actual):
                self.response.write_text(json.dumps(dict(success=True, data=dict(
                    number='42', title=self.order['title'], status='Developed', statusId=7,
                    content={'solution': {'text': actual}}))))
                result = self.invoke('verify')
                self.assertEqual(expected, result.returncode, result.stderr + result.stdout)
                report = json.loads((self.pack / 'remote-verification.json').read_text())
                self.assertEqual(bool(expected), bool(report['problems']))
                self.assertTrue((self.pack / 'LEVERANS-183.md').exists())
        self.assertEqual(2, len(self.calls.read_text().splitlines()))
        for call in self.calls.read_text().splitlines():
            self.assertEqual(['order', 'show', '--id', '42'], shlex.split(call)[:4])


if __name__ == '__main__':
    unittest.main()

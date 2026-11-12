import importlib.util
import contextlib
import io
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('deliver', Path(__file__).with_name('deliver.py'))
deliver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deliver)


class MarkdownCheckTests(unittest.TestCase):
    def test_all_dry_run_writes_request_markdown(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                item = dict(id='one', group='done', selected=True, directory='orders/one', stage='developed')
                if existing:
                    item['existingOrderId'] = 42
                manifest = dict(environment='development', sprint=183, items=[item],
                                choices=dict(requireCustomerAccept=False, shouldBeInvoiced=False))
                (root / 'orders/one').mkdir(parents=True)
                (root / 'manifest.json').write_text(json.dumps(manifest))
                (root / 'orders/one/order.json').write_text(json.dumps(dict(title='Test', solution='Klart.')))
                (root / 'readiness.json').write_text(json.dumps(dict(
                    duplicates=dict(matches=[]), fingerprint='local', utvTypeId=1, requesterId=1, api='https://example.com/')))
                output = io.StringIO()
                with patch.object(deliver.Cli, 'read', return_value=dict(
                    id=42, number='42', revision='REV', statusId=1)), contextlib.redirect_stdout(output):
                    self.assertEqual(0, deliver.run(deliver.Pack(root), dry_run=True))
                writes = [shlex.split(line[4:]) for line in output.getvalue().splitlines() if line.startswith('DRY ')]
                narratives = [args for args in writes if args[2] in ('create', 'update')]
                self.assertEqual(2, len(narratives))
                for args in narratives:
                    self.assertEqual('markdown', args[args.index('--format') + 1])
                self.assertFalse((root / 'ledger.json').exists())

    def test_solution_readback_projects_markdown(self):
        self.assertEqual('Uppgifter ligger kvar. Fokus behålls', deliver.solution_text(
            '**Uppgifter** ligger kvar.\n\n- Fokus behålls'))

    def test_markdown_sources_and_bullets_pass(self):
        order = dict(title='Bevara uppgifter', purpose='Att behålla uppgifter.',
                     customerNeed='Personal förlorade sina uppgifter.',
                     howIsItSolvedToday='De skriver in allt igen.',
                     solution='Uppgifterna ligger kvar.\n\n- Fokus behålls',
                     implementationDetails='Källor:\n- [PR 42](https://example.com/pr/42)',
                     note='Sprint 183 · arbete 1–12 nov 2026')
        self.assertEqual([], deliver.lint(order, Path('.')))

    def test_sources_still_belong_in_bullets(self):
        order = dict(implementationDetails='[Källa](https://example.com)')
        self.assertTrue(any('outside a bullet' in p for p in deliver.lint(order, Path('.'))))


if __name__ == '__main__':
    unittest.main()

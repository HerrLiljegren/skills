import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('collect', Path(__file__).with_name('collect.py'))
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


class CollectionTests(unittest.TestCase):
    def test_project_pagination_follows_next_command_and_row_repository(self):
        pr = dict(id=42, repository='Cli', project='Tengella', title='DEV-72',
                  closedDate='2026-11-01T12:00:00Z', createdDate='2026-10-31T12:00:00Z',
                  sourceRef='refs/heads/test', targetRef='refs/heads/master')
        pages = [dict(pullRequests=[pr], collection=dict(hasMore=True,
                 nextCommand='tengella devops pr list --author me --status completed --cursor next --json')),
                 dict(pullRequests=[dict(pr, id=43, repository='Tengella_bare')], collection=dict(hasMore=False))]
        with patch.object(collect, 'tengella', side_effect=pages) as cli:
            rows = collect.completed_prs('me', datetime(2026, 11, 1, tzinfo=timezone.utc),
                                         datetime(2026, 11, 2, tzinfo=timezone.utc))
        self.assertEqual(['Cli', 'Tengella_bare'], [r['repository'] for r in rows])
        self.assertNotIn('--repository', cli.call_args_list[0].args)
        self.assertIn('--closed-after', cli.call_args_list[0].args)
        self.assertEqual(('devops', 'pr', 'list', '--author', 'me', '--status', 'completed', '--cursor', 'next'),
                         cli.call_args_list[1].args)

    def test_missing_continuation_fails_instead_of_returning_partial_results(self):
        with patch.object(collect, 'tengella', return_value=dict(pullRequests=[], collection=dict(hasMore=True))):
            with self.assertRaises(SystemExit):
                collect.completed_prs('me', datetime.now(timezone.utc), datetime.now(timezone.utc))


if __name__ == '__main__':
    unittest.main()

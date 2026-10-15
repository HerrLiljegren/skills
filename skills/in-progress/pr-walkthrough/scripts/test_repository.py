"""Run with python3; no network or live Herdr session is used."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

LAUNCH = Path(__file__).with_name("launch.sh")
SSH = "git@ssh.dev.azure.com:v3/example/Project/Owner"
HTTPS = "https://example@dev.azure.com/example/Project/_git/Owner"


class RepositoryGuardTests(unittest.TestCase):
    def run_launcher(self, origin, metadata=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            info = {"source": "refs/heads/feature/same-name",
                    "target": "refs/heads/master", "title": "Review", "status": "active"}
            if metadata:
                info["repository"] = {"name": "Owner", "sshUrl": SSH, "remoteUrl": HTTPS}
            (root / "pr.json").write_text(json.dumps(info))
            scripts = {
                "az": '#!/bin/bash\ncat "$TEST_ROOT/pr.json"\n',
                "git": '''#!/bin/bash
[[ ${1:-} == -C ]] && shift 2
case "$*" in
  'rev-parse --show-toplevel') echo "$TEST_ROOT" ;;
  'remote get-url origin') echo "$TEST_ORIGIN" ;;
  fetch*) echo "$*" >> "$TEST_ROOT/fetches"; exit 1 ;;
  *) exit 90 ;;
esac
''',
                "wt": '#!/bin/bash\necho wt >> "$TEST_ROOT/operations"\necho \'{"repo":{"default_branch":"main"}}\'\n',
                "herdr": '#!/bin/bash\necho herdr >> "$TEST_ROOT/operations"\nexit 90\n',
                "hunk": '#!/bin/bash\nexit 90\n',
            }
            for name, body in scripts.items():
                path = root / name
                path.write_text(body)
                path.chmod(0o755)
            result = subprocess.run(["bash", str(LAUNCH), "5403"], text=True,
                                    capture_output=True, env={**os.environ,
                                        "PATH": f"{root}:{os.environ['PATH']}",
                                        "HERDR_ENV": "1", "TEST_ROOT": str(root),
                                        "TEST_ORIGIN": origin})
            fetches = (root / "fetches").read_text() if (root / "fetches").exists() else ""
            operations = (root / "operations").read_text() if (root / "operations").exists() else ""
            return result, fetches, operations

    def test_wrong_repository_stops_before_fetch_or_worktree(self):
        for origin in (SSH.replace("Owner", "Other"), SSH.replace("example", "other-org")):
            with self.subTest(origin=origin):
                result, fetches, operations = self.run_launcher(origin)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("PR 5403 belongs to Owner", result.stderr)
                self.assertEqual(fetches, "")
                self.assertEqual(operations, "")

    def test_matching_ssh_and_https_reach_target_fetch(self):
        for origin in (SSH, HTTPS, HTTPS.replace("example@", "") + ".git"):
            with self.subTest(origin=origin):
                result, fetches, _ = self.run_launcher(origin)
                self.assertIn("could not fetch origin/master", result.stderr)
                self.assertEqual(fetches, "fetch --quiet origin master\n")

    def test_missing_repository_metadata_stops_before_fetch(self):
        result, fetches, operations = self.run_launcher(SSH, metadata=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing repository identity", result.stderr)
        self.assertEqual(fetches, "")
        self.assertEqual(operations, "")


if __name__ == "__main__":
    unittest.main()

"""Offline contract checks: python3 -B scripts/test_check.py."""

import contextlib
import io
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import check


class ContractTests(unittest.TestCase):
    def fetch(self, path, params=None, *, raw=False):
        self.calls.append((path, params, raw))
        if path == "builds":
            definition = params["definitions"]
            self.assertEqual(params, {"definitions": definition, "statusFilter": "completed",
                                      "queryOrder": "queueTimeDescending", "$top": 1})
            if definition == self.missing:
                return {"value": []}
            return {"value": [{"id": definition * 100, "definition": {"id": definition, "name": "Nightly"},
                               "status": "completed", "result": self.results[definition]}]}
        if path == "resultsbybuild":
            if self.bad_tests:
                raise check.CheckError("Azure DevOps returned HTTP 404")
            return {"value": [{"runId": 7, "id": index} for index in range(3)]}
        if path == "runs/7/results":
            self.assertEqual(params["outcomes"], "Failed")
            return {"value": [{"automatedTestName": f"Suite.Test{index}", "automatedTestStorage": "suite.dll",
                               "errorMessage": "Unable to resolve service" if index < 2 else "Timeout",
                               "stackTrace": "   at Suite.Test()\n" * 20,
                               "failingSince": {"date": "2026-10-03", "build": {"number": "develop-4952"}}}
                              for index in range(3)]}
        if path.endswith("timeline"):
            if self.bad_timeline:
                raise check.CheckError("Azure DevOps returned HTTP 403")
            return {"records": [{"id": "step", "name": "Build", "type": "Task", "result": "failed",
                                 "issues": [{"type": "error", "message": "compile failed"}], "log": {"id": 3}}]}
        self.assertTrue(raw)
        return "\n".join(["context"] * 500 + ["##[error] CS1002: ; expected", "task failed"])

    def setUp(self):
        self.calls = []
        self.results = dict.fromkeys(check.DEFINITIONS, "succeeded")
        self.missing = None
        self.bad_timeline = False
        self.bad_tests = False

    def test_success_is_silent_and_never_fetches_logs(self):
        code, payload = check.check(self.fetch)
        self.assertEqual((code, payload), (0, None))
        self.assertEqual(len(self.calls), 3)
        output = io.StringIO()
        with patch.object(check, "check", return_value=(code, payload)), patch("sys.argv", ["check.py"]), contextlib.redirect_stdout(output):
            self.assertEqual(check.main(), 0)
        self.assertEqual(output.getvalue(), "")

    def test_each_unsuccessful_result_has_evidence(self):
        for result in ("failed", "partiallySucceeded", "canceled"):
            with self.subTest(result=result):
                self.results[54] = result
                code, payload = check.check(self.fetch)
                self.assertEqual(code, 1)
                step = payload["failures"][0]["steps"][0]
                self.assertEqual(step["errors"], ["compile failed"])
                self.assertIn("CS1002", str(step["log"]))
                self.assertLessEqual(len(step["log"]["lines"]), 128)
                self.assertTrue(step["log"]["truncated"])

    def test_failed_tests_are_grouped_by_assembly_and_error(self):
        self.results[54] = "failed"
        code, payload = check.check(self.fetch)
        self.assertEqual(code, 1)
        tests = payload["failures"][0]["test_failures"]
        self.assertEqual((tests["failed"], tests["truncated"]), (3, False))
        self.assertEqual([group["tests"] for group in tests["groups"]],
                         [["Suite.Test0", "Suite.Test1"], ["Suite.Test2"]])
        self.assertEqual(tests["groups"][0]["failing_since"], {"date": "2026-10-03", "build": "develop-4952"})
        self.assertEqual(len(tests["groups"][0]["stack"]), 10)

    def test_unavailable_test_results_is_lookup_error(self):
        self.results[54], self.bad_tests = "failed", True
        code, payload = check.check(self.fetch)
        self.assertEqual(code, 2)
        self.assertIn("404", payload["failures"][0]["test_lookup_error"])
        self.assertTrue(payload["failures"][0]["steps"])

    def test_missing_build_does_not_hide_other_failure(self):
        self.missing, self.results[55] = 54, "failed"
        code, payload = check.check(self.fetch)
        self.assertEqual(code, 2)
        self.assertEqual(payload["lookup_errors"][0]["definition_id"], 54)
        self.assertEqual(payload["failures"][0]["id"], 5500)

    def test_unavailable_timeline_retains_failed_build(self):
        self.results[54], self.bad_timeline = "failed", True
        code, payload = check.check(self.fetch)
        self.assertEqual(code, 2)
        self.assertEqual(payload["failures"][0]["id"], 5400)
        self.assertIn("403", payload["failures"][0]["lookup_error"])

    def test_unknown_result_is_lookup_error(self):
        self.results[54] = None
        self.assertEqual(check.check(self.fetch)[0], 2)

    def test_redacts_credentials(self):
        with patch.dict(os.environ, {"AZURE_DEVOPS_EXT_PAT": "test-credential"}):
            self.assertNotIn("test-credential", check.redact("test-credential password=private Bearer abc123"))
            self.assertNotIn("private", check.redact("password=private"))

    def test_cli_queries_are_explicit_and_use_argument_arrays(self):
        with patch.object(check.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, '{"value": []}', '')) as run:
            check.get("builds", {"definitions": 54, "statusFilter": "completed",
                                 "queryOrder": "queueTimeDescending", "$top": 1})
            command = run.call_args.args[0]
            self.assertEqual(command, ["az", "devops", "invoke", "--organization", check.ORGANIZATION,
                "--detect", "false", "--area", "build", "--resource", "builds",
                "--http-method", "GET", "--api-version", "7.1", "--only-show-errors",
                "--output", "json", "--route-parameters", "project=Tengella", "--query-parameters",
                "definitions=54", "statusFilter=completed", "queryOrder=queueTimeDescending", "$top=1"])
            self.assertEqual(run.call_args.kwargs["env"]["AZURE_EXTENSION_USE_DYNAMIC_INSTALL"], "no")
            check.get("builds/5400/timeline")
            self.assertIn("timeline", run.call_args.args[0])
            self.assertIn("buildId=5400", run.call_args.args[0])
            check.get("resultsbybuild", {"buildId": 5400})
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--area") + 1], "testresults")
            self.assertEqual(command[command.index("--api-version") + 1], "7.1-preview")
            check.get("runs/7/results", {"outcomes": "Failed"})
            self.assertIn("runId=7", run.call_args.args[0])

    def test_cli_log_files_are_read_and_deleted(self):
        paths = []
        def execute(command, **kwargs):
            path = Path(command[command.index("--out-file") + 1])
            paths.append(path)
            self.assertIn("logs", command)
            self.assertIn("logId=3", command)
            self.assertIn("text/plain", command)
            path.write_text("##[error] compilation failed\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, '', '')
        with patch.object(check.subprocess, "run", side_effect=execute):
            self.assertIn("compilation failed", check.get("builds/5400/logs/3", raw=True))
        self.assertFalse(paths[0].exists())

    def test_cli_error_timeout_and_invalid_json_are_check_errors(self):
        for response in (subprocess.CompletedProcess([], 1, '', 'ERROR: TF400813: user identity denied'),
                         subprocess.CompletedProcess([], 0, '<html>login</html>', '')):
            with self.subTest(response=response), patch.object(check.subprocess, "run", return_value=response):
                with self.assertRaises(check.CheckError):
                    check.get("builds")
        with patch.object(check.subprocess, "run", side_effect=subprocess.TimeoutExpired("az", 45)):
            with self.assertRaisesRegex(check.CheckError, "timeout"):
                check.get("builds")


if __name__ == "__main__":
    unittest.main()

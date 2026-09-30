"""Offline contract checks: python3 -B scripts/test_check.py."""

import contextlib
import io
import os
import unittest
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

    def test_redacts_credentials_and_rejects_redirects(self):
        with patch.dict(os.environ, {"PERSONAL_ACCESS_TOKEN": "test-credential"}):
            self.assertNotIn("test-credential", check.redact("test-credential password=private Bearer abc123"))
            self.assertNotIn("private", check.redact("password=private"))
        with self.assertRaises(check.CheckError):
            check.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example")


if __name__ == "__main__":
    unittest.main()

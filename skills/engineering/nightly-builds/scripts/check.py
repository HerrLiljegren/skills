#!/usr/bin/env python3
"""Read-only, deterministic build evidence through the Azure DevOps CLI."""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ORGANIZATION = "https://dev.azure.com/tengella"
PROJECT = "Tengella"
BASE = f"{ORGANIZATION}/{PROJECT}"
DEFINITIONS = (54, 55, 53)
TEST_RESULT_LIMIT = 200
TEST_DETAIL_LIMIT = 50
ERROR = re.compile(r"##\[error\]|\berror\b|exception|\bfailed\b|failure|fatal", re.I)


class CheckError(Exception):
    pass


def redact(text):
    token = os.environ.get("AZURE_DEVOPS_EXT_PAT", "")
    if token:
        text = text.replace(token, "[REDACTED]")
        encoded = base64.b64encode((":" + token).encode()).decode()
        text = text.replace(encoded, "[REDACTED]")
    text = re.sub(r"(?i)(\b(?:password|token|secret|api[_-]?key|authorization|sig)\b\s*[=:]\s*)[^\s;&]+",
                  r"\1[REDACTED]", text)
    return re.sub(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9+/._=-]+", r"\1 [REDACTED]", text)


def get(path, params=None, *, raw=False):
    parts = path.split("/")
    routes = [f"project={PROJECT}"]
    area, version = "build", "7.1"
    if parts == ["builds"]:
        resource = "builds"
    elif len(parts) == 3 and parts[0] == "builds" and parts[2] == "timeline":
        resource = "timeline"
        routes.append(f"buildId={int(parts[1])}")
    elif len(parts) == 4 and parts[0] == "builds" and parts[2] == "logs":
        resource = "logs"
        routes.extend((f"buildId={int(parts[1])}", f"logId={int(parts[3])}"))
    elif parts == ["resultsbybuild"]:
        # Only this preview route lists results by build; test/runs resolves to a statistics route.
        area, resource, version = "testresults", "resultsbybuild", "7.1-preview"
    elif len(parts) == 3 and parts[0] == "runs" and parts[2] == "results":
        area, resource = "test", "results"
        routes.append(f"runId={int(parts[1])}")
    else:
        raise CheckError("Unsupported build lookup")
    command = ["az", "devops", "invoke", "--organization", ORGANIZATION,
               "--detect", "false", "--area", area, "--resource", resource,
               "--http-method", "GET", "--api-version", version,
               "--only-show-errors", "--output", "json", "--route-parameters", *routes]
    if params:
        command.extend(("--query-parameters", *(f"{key}={value}" for key, value in params.items())))
    environment = {**os.environ, "AZURE_EXTENSION_USE_DYNAMIC_INSTALL": "no",
                   "AZURE_CORE_COLLECT_TELEMETRY": "no", "AZURE_LOGGING_ENABLE_LOG_FILE": "false"}
    try:
        # invoke requires --out-file for text logs. Keep raw logs private and ephemeral.
        with tempfile.TemporaryDirectory(prefix="nightly-builds-") as directory:
            log = Path(directory) / "log.txt"
            if raw:
                command.extend(("--accept-media-type", "text/plain", "--out-file", str(log)))
            response = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                      timeout=45, env=environment)
            if response.returncode:
                message = redact(response.stderr.strip())
                if "TF400813" in message:
                    message = "Azure DevOps authorization failed (TF400813)"
                raise CheckError(message[:2000] or f"az devops invoke exited {response.returncode}")
            return log.read_text(encoding="utf-8-sig") if raw else json.loads(response.stdout)
    except FileNotFoundError:
        raise CheckError("Azure CLI or requested log output is missing") from None
    except subprocess.TimeoutExpired:
        raise CheckError("az devops invoke exceeded the 45-second timeout") from None
    except OSError:
        raise CheckError("Unable to run az devops invoke or read its output") from None
    except (ValueError, UnicodeError):
        raise CheckError("Azure DevOps returned an invalid API response") from None


def excerpt(text):
    lines = text.splitlines()
    selected = set(range(max(0, len(lines) - 20), len(lines)))
    # Bound excerpts deterministically: first error contexts plus the task tail.
    for index, line in enumerate(lines):
        if ERROR.search(line):
            selected.update(range(max(0, index - 3), min(len(lines), index + 5)))
            if len(selected) >= 120:
                break
    return {"total_lines": len(lines), "truncated": len(selected) < len(lines),
            "lines": [{"line": index + 1, "text": redact(lines[index])[:2000]}
                      for index in sorted(selected)]}


def test_failures(build_id, fetch):
    listed = fetch("resultsbybuild", {"buildId": build_id, "outcomes": "Failed",
                                      "$top": TEST_RESULT_LIMIT})["value"]
    evidence = {"failed": len(listed), "truncated": len(listed) >= TEST_RESULT_LIMIT, "groups": []}
    groups = {}
    remaining = TEST_DETAIL_LIMIT
    for run_id in sorted({int(row["runId"]) for row in listed}):
        if remaining <= 0:
            evidence["truncated"] = True
            break
        rows = fetch(f"runs/{run_id}/results", {"outcomes": "Failed", "$top": remaining})["value"]
        remaining -= len(rows)
        for row in rows:
            message = redact(row.get("errorMessage") or "")[:1000]
            # Group by assembly and error so one root cause does not repeat per test.
            key = (row.get("automatedTestStorage"), message)
            group = groups.get(key)
            if group is None:
                since = row.get("failingSince") or {}
                group = groups[key] = {
                    "storage": row.get("automatedTestStorage"), "error": message,
                    "stack": [redact(line)[:300] for line in (row.get("stackTrace") or "").splitlines()[:10]],
                    "failing_since": {"date": since.get("date"),
                                      "build": (since.get("build") or {}).get("number")},
                    "run_url": f"{BASE}/_TestManagement/Runs?runId={run_id}", "tests": []}
                evidence["groups"].append(group)
            group["tests"].append(row.get("automatedTestName") or row.get("testCaseTitle"))
    if len(listed) > TEST_DETAIL_LIMIT:
        evidence["truncated"] = True
    return evidence


def inspect(build, fetch):
    build_id = int(build["id"])
    evidence = {key: build.get(key) for key in
                ("id", "buildNumber", "result", "reason", "queueTime", "finishTime", "sourceBranch", "sourceVersion")}
    evidence.update(definition=build["definition"],
                    url=f"{BASE}/_build/results?buildId={build_id}", steps=[])
    timeline = fetch(f"builds/{build_id}/timeline")
    records = sorted(timeline["records"],
                     key=lambda row: (row.get("order", 0), row.get("attempt", 1), row["id"]))
    for row in records:
        issues = [issue for issue in row.get("issues", []) if issue.get("type") == "error"]
        if row.get("result") not in ("failed", "partiallySucceeded", "canceled", "abandoned") and not issues:
            continue
        step = {key: row.get(key) for key in ("id", "parentId", "type", "name", "result", "attempt")}
        step["errors"] = [redact(issue.get("message", "")) for issue in issues]
        log_id = (row.get("log") or {}).get("id")
        if log_id:
            step.update(log_id=log_id, log_url=f"{BASE}/_build/results?buildId={build_id}&view=logs&j={row['id']}")
            try:
                step["log"] = excerpt(fetch(f"builds/{build_id}/logs/{int(log_id)}", raw=True))
            except CheckError as error:
                step["lookup_error"] = str(error)
        evidence["steps"].append(step)
    try:
        evidence["test_failures"] = test_failures(build_id, fetch)
    except (CheckError, KeyError, TypeError, ValueError) as error:
        evidence["test_lookup_error"] = str(error) if isinstance(error, CheckError) else "Malformed test results response"
    if not evidence["steps"]:
        evidence["evidence_gap"] = "No failing steps or error issues in the timeline; cause undetermined"
    return evidence


def check(fetch=get):
    failures, errors = [], []
    for definition in DEFINITIONS:
        try:
            # Query each definition separately so a busy pipeline cannot crowd out another.
            response = fetch("builds", {"definitions": definition, "statusFilter": "completed",
                                        "queryOrder": "queueTimeDescending", "$top": 1})
            builds = response["value"]
            if not builds:
                raise CheckError("No completed run exists")
            build = builds[0]
            if build["definition"]["id"] != definition or build["status"] != "completed":
                raise CheckError("API response does not match the requested definition and completed status")
            if build.get("result") == "succeeded":
                continue
            if build.get("result") not in ("failed", "partiallySucceeded", "canceled"):
                raise CheckError("Completed build has an unknown result")
            # Retain the failure identity even when its timeline cannot be retrieved.
            try:
                failure = inspect(build, fetch)
            except (CheckError, KeyError, TypeError, ValueError) as error:
                failure = {"id": build["id"], "definition": build["definition"], "result": build["result"],
                           "url": f"{BASE}/_build/results?buildId={build['id']}",
                           "lookup_error": str(error) if isinstance(error, CheckError) else "Malformed timeline response"}
            failures.append(failure)
            if failure.get("lookup_error") or failure.get("test_lookup_error") or any(step.get("lookup_error") for step in failure.get("steps", [])):
                errors.append({"definition_id": definition, "error": "Failure evidence lookup incomplete"})
        except (CheckError, KeyError, TypeError, ValueError) as error:
            errors.append({"definition_id": definition,
                           "error": str(error) if isinstance(error, CheckError) else "Malformed API response"})
    if not failures and not errors:
        return 0, None
    return (2 if errors else 1), {"failures": failures, "lookup_errors": errors}


def main():
    parser = argparse.ArgumentParser(description=(
        "Check latest completed runs of definitions 54, 55, 53 (queue time descending, all reasons). "
        "Stdout is empty on success (exit 0); JSON failure evidence, including failed test results "
        "grouped by assembly and error, exits 1; "
        "incomplete lookup exits 2. Uses az devops invoke with existing Azure CLI authentication "
        "or AZURE_DEVOPS_EXT_PAT. No alternate lookup methods."))
    parser.add_argument("--build-id", type=int)
    parser.add_argument("--log-id", type=int)
    parser.add_argument("--start-line", type=int)
    parser.add_argument("--end-line", type=int)
    args = parser.parse_args()
    values = (args.build_id, args.log_id, args.start_line, args.end_line)
    if any(value is not None for value in values):
        if any(value is None or value < 1 for value in values) or not 0 <= args.end_line - args.start_line < 200:
            parser.error("log lookup requires four positive IDs/line numbers and a range of at most 200 lines")
        try:
            log = get(f"builds/{args.build_id}/logs/{args.log_id}", raw=True)
            payload = {"build_id": args.build_id, "log_id": args.log_id,
                       "lines": [{"line": args.start_line + index, "text": redact(line)[:2000]}
                                 for index, line in enumerate(log.splitlines()[args.start_line - 1:args.end_line])]}
            code = 0
        except CheckError as error:
            code, payload = 2, {"lookup_error": str(error)}
    else:
        code, payload = check()
    if payload is not None:
        print(redact(json.dumps(payload, indent=2)))
    return code


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Read-only, deterministic Azure DevOps build evidence. Requires PERSONAL_ACCESS_TOKEN."""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://dev.azure.com/tengella/Tengella"
DEFINITIONS = (54, 55, 53)
ERROR = re.compile(r"##\[error\]|\berror\b|exception|\bfailed\b|failure|fatal", re.I)


class CheckError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Keep the Authorization header confined to the configured API host.
        raise CheckError("Azure DevOps redirected the request; repair API access")


def redact(text):
    token = os.environ.get("PERSONAL_ACCESS_TOKEN", "")
    if token:
        text = text.replace(token, "[REDACTED]")
        encoded = base64.b64encode((":" + token).encode()).decode()
        text = text.replace(encoded, "[REDACTED]")
    text = re.sub(r"(?i)(\b(?:password|token|secret|api[_-]?key|authorization|sig)\b\s*[=:]\s*)[^\s;&]+",
                  r"\1[REDACTED]", text)
    return re.sub(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9+/._=-]+", r"\1 [REDACTED]", text)


def get(path, params=None, *, raw=False):
    token = os.environ.get("PERSONAL_ACCESS_TOKEN")
    if not token:
        raise CheckError("PERSONAL_ACCESS_TOKEN is missing; load the configured Azure DevOps credential")
    query = urllib.parse.urlencode({"api-version": "7.1", **(params or {})})
    request = urllib.request.Request(
        f"{BASE}/_apis/build/{path}?{query}",
        headers={"Authorization": "Basic " + base64.b64encode((":" + token).encode()).decode(),
                 "Accept": "text/plain" if raw else "application/json"},
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            # A login page must never be mistaken for a successful API lookup.
            if raw and "text/plain" not in response.headers.get("Content-Type", ""):
                raise CheckError("Log API did not return text/plain")
            body = response.read().decode("utf-8-sig")
        return body if raw else json.loads(body)
    except urllib.error.HTTPError as error:
        raise CheckError(f"Azure DevOps returned HTTP {error.code}") from None
    except OSError:
        raise CheckError("Azure DevOps network lookup failed") from None
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
            if failure.get("lookup_error") or any(step.get("lookup_error") for step in failure.get("steps", [])):
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
        "Stdout is empty on success (exit 0); JSON failure evidence exits 1; "
        "incomplete lookup exits 2. Auth: PERSONAL_ACCESS_TOKEN only. No retries or alternate auth."))
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

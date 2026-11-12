#!/usr/bin/env python3
"""Check a PR body against the pr skill's template before it is published.

Errors fail the check (exit 1): a missing section, an unfilled template placeholder, a body over the
host's length limit, or (unless --draft) an empty verdict. Warnings print but do not fail: things a
reviewer cannot use, such as local file paths, full commit SHAs and claims about a run instead of
the run itself.

Usage: check_body.py <body.md> [--host azure|github] [--draft]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Azure DevOps rejects PR descriptions over 4000 characters; GitHub allows 65536.
LIMITS = {"azure": 4000, "github": 65536}

REQUIRED = [
    (r"^\*\*Solves:\*\*\s*\S", "a '**Solves:**' line"),
    (r"^## Summary\s*$", "a '## Summary' section"),
    (r"^## Evidence\s*$", "a '## Evidence' section"),
    (r"^\*\*Verdict:\*\*", "a '**Verdict:**' line"),
    (r"^## Merge Danger\s*$", "a '## Merge Danger' section"),
    (r"^\*\*Door:\*\*\s*(one-way|two-way)\b", "'**Door:**' set to one-way or two-way"),
    (r"^\*\*Blast Radius:\*\*\s*\S", "a '**Blast Radius:**' value"),
    (r"^\*\*Risk call:\*\*\s*\S", "a '**Risk call:**' value"),
]

VERDICT = re.compile(r"^\*\*Verdict:\*\*\s*(PASS\+NOTES|PASS|FAIL)\b", re.M)
# Template placeholders look like "<one line, in the issue's terms>": lowercase words with a space.
PLACEHOLDER = re.compile(r"<[a-z][a-z ,'/:;-]* [a-z ,'/:;-]+>")
LOCAL_PATH = re.compile(r"(?<![\w/.])(/home/|/tmp/|/Users/|[A-Za-z]:\\Users\\)\S*")
FULL_SHA = re.compile(r"\b[0-9a-f]{40}\b")
TELLING = re.compile(
    r"\b(verified locally|all (the )?tests pass(ed)?|review passed|tests are green|works on my machine)\b",
    re.I,
)


def prose(text: str) -> str:
    """Return the body without fenced code blocks and inline code, which may hold anything."""
    text = re.sub(r"^(```|~~~).*?^\1\s*$", "", text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def check(text: str, host: str, draft: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    outside_code = prose(text)

    for pattern, what in REQUIRED:
        if not re.search(pattern, outside_code, re.M | re.I):
            errors.append(f"missing {what}")

    if not draft and re.search(r"^\*\*Verdict:\*\*", outside_code, re.M) and not VERDICT.search(outside_code):
        errors.append("verdict is not PASS, PASS+NOTES or FAIL (use --draft before verification)")

    for match in sorted(set(PLACEHOLDER.findall(outside_code))):
        errors.append(f"unfilled placeholder {match}")

    limit = LIMITS[host]
    if len(text) > limit:
        errors.append(f"{len(text)} characters, over the {host} limit of {limit} by {len(text) - limit}")

    for match in sorted({m.group(0) for m in LOCAL_PATH.finditer(outside_code)}):
        warnings.append(f"local path the reviewer cannot open: {match}")
    if FULL_SHA.search(outside_code):
        warnings.append("full commit SHA in the body; link the commit instead")
    for match in sorted({m.group(0).lower() for m in TELLING.finditer(outside_code)}):
        warnings.append(f"claim about a run ('{match}'); show the run or leave it to CI")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("body", type=Path)
    parser.add_argument("--host", choices=sorted(LIMITS), default="azure")
    parser.add_argument("--draft", action="store_true", help="allow an empty verdict before verification")
    args = parser.parse_args()

    errors, warnings = check(args.body.read_text(encoding="utf-8"), args.host, args.draft)
    for line in errors:
        print(f"error   {line}")
    for line in warnings:
        print(f"warning {line}")
    status = "FAIL" if errors else "PASS"
    print(f"{status} {args.body} ({len(errors)} errors, {len(warnings)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

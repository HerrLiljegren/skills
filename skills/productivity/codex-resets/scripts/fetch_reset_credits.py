#!/usr/bin/env python3
"""Fetch Codex reset credits and print a sanitized Markdown table."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


URL = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
AUTH_PATH = Path("~/.codex/auth.json").expanduser()


class SafeError(RuntimeError):
    """An error message safe to show to the user."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a safe Markdown table of Codex reset credits."
    )
    parser.add_argument(
        "--auth",
        default=str(AUTH_PATH),
        help="Path to Codex auth JSON. Defaults to ~/.codex/auth.json.",
    )
    parser.add_argument(
        "--url",
        default=URL,
        help="Reset credits endpoint. Defaults to the ChatGPT backend endpoint.",
    )
    return parser.parse_args()


def load_access_token(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SafeError(f"Auth file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SafeError("Auth file is not valid JSON.") from exc
    except OSError as exc:
        raise SafeError(f"Could not read auth file: {path}") from exc

    token = get_path(data, ("tokens", "access_token")) or get_path(data, ("access_token",))
    if not isinstance(token, str) or not token.strip():
        raise SafeError("No access token found in the auth file.")
    return token


def get_path(data: Any, path: tuple[str, ...]) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def fetch_credits(url: str, access_token: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "codex-resets-skill",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise SafeError(f"Reset credits request failed with HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise SafeError("Reset credits request failed before receiving a response.") from exc
    except TimeoutError as exc:
        raise SafeError("Reset credits request timed out.") from exc

    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SafeError("Reset credits response was not valid JSON.") from exc

    credits = data.get("credits") if isinstance(data, dict) else None
    if not isinstance(credits, list):
        raise SafeError("Reset credits response did not contain a credits list.")

    return [credit for credit in credits if isinstance(credit, dict)]


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def datetime_cell(value: Any) -> str:
    parsed = parse_datetime(value)
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M %Z") if parsed else ""


def days_until_expiry(value: Any, now: datetime) -> str:
    expires_at = parse_datetime(value)
    if not expires_at:
        return ""

    seconds = (expires_at - now).total_seconds()
    return str(math.ceil(seconds / 86400))


def redeemed_cell(credit: dict[str, Any]) -> str:
    redeemed_at = parse_datetime(credit.get("redeemed_at"))
    redeem_started_at = parse_datetime(credit.get("redeem_started_at"))

    if redeemed_at:
        return f"Yes ({datetime_cell(credit.get('redeemed_at'))})"
    if redeem_started_at:
        return f"Started ({datetime_cell(credit.get('redeem_started_at'))})"
    return "No"


def status_cell(credit: dict[str, Any], now: datetime) -> str:
    if parse_datetime(credit.get("redeemed_at")):
        return "Redeemed"
    if parse_datetime(credit.get("redeem_started_at")):
        return "Redeem started"

    expires_at = parse_datetime(credit.get("expires_at"))
    if expires_at and expires_at < now:
        return "Expired"
    return "Available"


def available_cell(credit: dict[str, Any], now: datetime) -> str:
    return "1" if status_cell(credit, now) == "Available" else "0"


def markdown_escape(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    return text.strip()


def render_table(credits: list[dict[str, Any]], now: datetime) -> str:
    headers = [
        "Available credits",
        "Status",
        "Reset",
        "Issued date/time",
        "Expiry date/time",
        "Days until expiry",
        "Redeemed",
    ]

    rows = []
    for credit in sorted(
        credits, key=lambda item: datetime_cell(item.get("expires_at"))
    ):
        rows.append(
            [
                available_cell(credit, now),
                status_cell(credit, now),
                credit.get("title", ""),
                datetime_cell(credit.get("granted_at")),
                datetime_cell(credit.get("expires_at")),
                days_until_expiry(credit.get("expires_at"), now),
                redeemed_cell(credit),
            ]
        )

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(markdown_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        token = load_access_token(Path(args.auth).expanduser())
        credits = fetch_credits(args.url, token)
        print(render_table(credits, datetime.now(timezone.utc)))
    except SafeError as exc:
        print(f"codex-resets: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

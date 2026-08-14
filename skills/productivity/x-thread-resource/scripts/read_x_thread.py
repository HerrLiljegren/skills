#!/usr/bin/env python3
"""Read an X/Twitter thread through twitter-thread.com's unroll endpoint."""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
from dataclasses import dataclass, asdict
from datetime import date
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler


STATUS_RE = re.compile(r"/status(?:es)?/(\d+)")
HTTP_RE = re.compile(r"https?://[^\s<>)\"']+")
MAX_LINKS = 5
MAX_BYTES = 200_000
TIMEOUT = 12


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_safe_public_url(newurl):
            raise RuntimeError(f"blocked unsafe redirect: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.in_title = False
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() != "meta":
            return
        key = attrs_dict.get("property") or attrs_dict.get("name")
        content = attrs_dict.get("content")
        if key and content:
            self.meta[key.lower()] = html.unescape(content).strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str | None:
        candidates = [
            self.meta.get("og:title"),
            self.meta.get("twitter:title"),
            " ".join(self.title_parts).strip(),
        ]
        return next((compact(value) for value in candidates if value and compact(value)), None)

    @property
    def description(self) -> str | None:
        candidates = [
            self.meta.get("og:description"),
            self.meta.get("twitter:description"),
            self.meta.get("description"),
        ]
        return next((compact(value) for value in candidates if value and compact(value)), None)


@dataclass
class LinkPreview:
    url: str
    ok: bool
    final_url: str | None = None
    title: str | None = None
    description: str | None = None
    content_type: str | None = None
    error: str | None = None


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def status_id(value: str) -> str:
    if value.isdigit():
        return value
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if parsed.hostname not in {"x.com", "twitter.com", "mobile.twitter.com"}:
        raise ValueError("expected an x.com, twitter.com, mobile.twitter.com URL, or a numeric status id")
    match = STATUS_RE.search(parsed.path)
    if not match:
        raise ValueError("could not find a status id in the URL")
    return match.group(1)


def is_safe_public_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.port and parsed.port not in {80, 443}:
        return False
    host = parsed.hostname
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            return False
    return True


def fetch_json(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "x-thread-resource/1.0"})
    try:
        with build_opener().open(req, timeout=TIMEOUT) as response:
            body = response.read(MAX_BYTES + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"endpoint request failed: {exc}") from exc
    if len(body) > MAX_BYTES:
        raise RuntimeError("endpoint response exceeded size limit")
    return json.loads(body.decode("utf-8"))


def fetch_link_preview(url: str) -> LinkPreview:
    if not is_safe_public_url(url):
        return LinkPreview(url=url, ok=False, error="blocked unsafe or non-public URL")
    req = Request(
        url,
        headers={
            "User-Agent": "x-thread-resource/1.0",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.1",
            "Range": f"bytes=0-{MAX_BYTES - 1}",
        },
    )
    context = ssl.create_default_context()
    opener = build_opener(SafeRedirect, HTTPSHandler(context=context))
    try:
        with opener.open(req, timeout=TIMEOUT) as response:
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "")
            body = response.read(MAX_BYTES + 1)
    except Exception as exc:
        return LinkPreview(url=url, ok=False, error=str(exc))
    if len(body) > MAX_BYTES:
        return LinkPreview(url=url, ok=False, final_url=final_url, content_type=content_type, error="response exceeded size limit")
    if not content_type.lower().startswith(("text/html", "application/xhtml+xml", "text/plain")):
        return LinkPreview(url=url, ok=False, final_url=final_url, content_type=content_type, error="unsupported content type")
    text = body.decode("utf-8", errors="replace")
    parser = MetadataParser()
    parser.feed(text)
    return LinkPreview(
        url=url,
        ok=True,
        final_url=final_url,
        title=parser.title,
        description=parser.description,
        content_type=content_type,
    )


def extract_links(thread: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    links: list[str] = []
    for tweet in thread.get("tweets") or []:
        for url in HTTP_RE.findall(tweet.get("text") or ""):
            cleaned = url.rstrip(".,;:")
            if cleaned not in seen:
                seen.add(cleaned)
                links.append(cleaned)
        for entity in ((tweet.get("urls") or []) + ((tweet.get("entities") or {}).get("urls") or [])):
            expanded = entity.get("expanded_url") or entity.get("url")
            if expanded and expanded not in seen:
                seen.add(expanded)
                links.append(expanded)
    return links


def media_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if not isinstance(value, dict):
        return None
    candidates = [
        value.get("url"),
        value.get("media_url_https"),
        value.get("media_url"),
        value.get("preview_image_url"),
        value.get("thumbnail_url"),
    ]
    variants = value.get("variants")
    if isinstance(variants, list):
        candidates.extend(variant.get("url") for variant in variants if isinstance(variant, dict))
    return next((candidate for candidate in candidates if isinstance(candidate, str) and candidate.startswith(("http://", "https://"))), None)


def extract_media(thread: dict[str, Any]) -> list[dict[str, str]]:
    seen: set[str] = set()
    media: list[dict[str, str]] = []
    fields = ("photos", "video", "media", "extended_entities")
    for tweet in thread.get("tweets") or []:
        tweet_id = str(tweet.get("id") or "")
        values: list[Any] = []
        for field in fields:
            value = tweet.get(field)
            if isinstance(value, list):
                values.extend(value)
            elif isinstance(value, dict):
                nested = value.get("media")
                if isinstance(nested, list):
                    values.extend(nested)
                else:
                    values.append(value)
            elif value:
                values.append(value)
        for value in values:
            url = media_url(value)
            if not url or url in seen:
                continue
            seen.add(url)
            kind = value.get("type", "media") if isinstance(value, dict) else "media"
            media.append({"tweetId": tweet_id, "type": str(kind), "url": url})
    return media


def read_thread(value: str, follow_links: bool) -> dict[str, Any]:
    sid = status_id(value)
    endpoint = f"https://twitter-thread.com/api/unroll-thread?id={sid}"
    payload = fetch_json(endpoint)
    if not payload.get("ok") or not payload.get("thread"):
        raise RuntimeError("twitter-thread endpoint did not return a thread")
    thread = payload["thread"]
    links = extract_links(thread)
    media = extract_media(thread)
    previews = [fetch_link_preview(url) for url in links[:MAX_LINKS]] if follow_links else []
    return {
        "captured": date.today().isoformat(),
        "endpoint": endpoint,
        "thread": thread,
        "links": links,
        "media": media,
        "linkPreviews": [asdict(preview) for preview in previews],
    }


def markdown(result: dict[str, Any]) -> str:
    thread = result["thread"]
    author = thread.get("author") or {}
    tweets = thread.get("tweets") or []
    lines = [
        f"# {thread.get('title') or 'X thread'}",
        "",
        f"Source: [{author.get('username', 'unknown')} on X]({thread.get('url')})",
        f"Thread reader: [{thread.get('id')}]({thread.get('threadUrl')})",
        f"Author: {author.get('name', 'Unknown')} (@{author.get('username', 'unknown')})",
        f"Captured: {result['captured']}",
        f"Thread id: {thread.get('id')}",
        "",
        "## Thread",
        "",
    ]
    for index, tweet in enumerate(tweets, start=1):
        text = (tweet.get("text") or "").strip()
        created = tweet.get("createdAt") or "Unknown date"
        lines.append(f"{index}. {created}")
        for paragraph in text.splitlines():
            if paragraph.strip():
                lines.append(f"   {paragraph.strip()}")
        lines.append("")
    if result.get("linkPreviews"):
        lines.extend(["## Linked sources", ""])
        for preview in result["linkPreviews"]:
            status = "ok" if preview["ok"] else f"blocked: {preview.get('error')}"
            lines.append(f"- {preview['url']} ({status})")
            if preview.get("title"):
                lines.append(f"  - Title: {preview['title']}")
            if preview.get("description"):
                lines.append(f"  - Description: {preview['description']}")
        lines.append("")
    if result.get("media"):
        lines.extend(["## Thread media", ""])
        for item in result["media"]:
            lines.append(f"- Tweet {item.get('tweetId')}: {item.get('type')} - {item.get('url')}")
        lines.append("")
    lines.extend([
        "## Retrieval handles",
        "",
        f"- @{author.get('username', 'unknown')}, {author.get('name', 'Unknown')}, {thread.get('id')}, {thread.get('url')}, {thread.get('threadUrl')}",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url_or_id")
    parser.add_argument("--no-follow-links", action="store_true", help="only unroll the thread")
    parser.add_argument("--json", action="store_true", help="emit structured JSON")
    args = parser.parse_args()
    try:
        result = read_thread(args.url_or_id, follow_links=not args.no_follow_links)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

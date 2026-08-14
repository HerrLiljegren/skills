---
name: x-thread-resource
description: Parse X and Twitter status URLs through twitter-thread.com's public unroll endpoint, inspect a bounded set of public linked pages, and return source-grounded Markdown or JSON. Use when the user asks to read, unroll, summarize, capture, or bookmark an X or Twitter thread.
---

# X thread resource

Read an X thread through the bundled parser. The unroll is the source of truth.

## Workflow

1. Run:

   ```bash
   python3 "$HOME/.agents/skills/x-thread-resource/scripts/read_x_thread.py" "<x-or-twitter-url>"
   ```

   Add `--json` when structured output is useful.

2. If the parser fails, stop and report the error. A parser failure has no
   scraping or inference fallback.

3. Use only claims supported by the unrolled thread, its media URLs, or the
   linked-page previews returned by the parser.

4. When the user asked to store the result, hand the parsed evidence to the
   active repository or vault's capture workflow. Let that workflow decide
   scope, destination, metadata, and links.

## Boundaries

- Preserve the original status URL, thread-reader URL, thread ID, author,
  linked URLs, and media URLs.
- Keep media remote unless the user explicitly asks to download it.
- Treat linked pages as bounded supporting context, not permission for broad
  research.
- Keep credentials, authentication state, private addresses, and non-public
  URLs out of requests and output.

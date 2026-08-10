---
name: codex-resets
description: Fetch and render the user's Codex reset credits from the ChatGPT rate-limit reset credits endpoint using ~/.codex/auth.json. Use when the user asks about Codex reset credits, reset credit expiry, available resets, redeemed reset status, or wants a safe Markdown table of Codex reset credits without exposing auth tokens or raw API data.
---

# Codex Resets

Fetch Codex reset credits and render only a sanitized Markdown table.

## Workflow

1. Run the bundled script with network access on the first attempt:

   ```bash
   python "$HOME/.agents/skills/codex-resets/scripts/fetch_reset_credits.py"
   ```

   In Codex, call `exec_command` with:

   - `sandbox_permissions: require_escalated`
   - a justification that the script contacts the ChatGPT endpoint and returns
     only sanitized output

   This step is complete when the script exits successfully and prints the
   Markdown table.

2. Return the table as-is unless the user asks for a shorter summary.

3. If the network-enabled execution fails, return only its safe error message.
   Keep `~/.codex/auth.json`, tokens, API response bodies, and raw JSON out of
   debugging and user-visible output.

## Output Rules

- Render a Markdown table with these columns only:
  `Available credits`, `Status`, `Reset`, `Issued date/time`, `Expiry date/time`, `Days until expiry`, `Redeemed`.
- Read `credits[].granted_at` as the issued date and time.
- Read `credits[].expires_at` as the expiry date and time.
- Render timestamps in the machine's local timezone as `YYYY-MM-DD HH:MM TZ`.
- Read `credits[].title` as the reset type.
- Use `credits[].redeemed_at` and `credits[].redeem_started_at` for redeemed status.
- Treat a credit as available only when it is not redeemed, redemption has not started, and the expiry date has not passed.
- Escape Markdown table control characters in rendered values.

## Safety Rules

- Never expose tokens, auth JSON, account IDs, credit IDs, profile user IDs, image URLs, or raw API responses.
- Never add debug logging that prints request headers, auth file content, response bodies, or full exceptions containing payloads.
- If extra fields are present in the API response, ignore them.
- If an expected field is missing, render an empty safe cell or a generic safe status rather than printing the object.

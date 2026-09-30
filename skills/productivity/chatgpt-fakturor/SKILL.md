---
name: chatgpt-fakturor
description: Download or email selected ChatGPT invoice and receipt PDFs.
disable-model-invocation: true
---
# ChatGPT fakturor

Download the requested ChatGPT subscription billing documents into
`~/Downloads/chatgpt-fakturor`. When asked, prepare an email with the verified
documents attached.

## Workflow

1. Use the Codex built-in browser (IAB). If it is not signed in, leave the
   sign-in page ready and ask the user to sign in; never request or handle
   their password, OTP, or recovery codes.
2. Resolve the request before browsing:
   - `latest` means the newest paid transaction shown in **Transaction history**.
   - Download only the requested document type: invoice, receipt, or both.
   - Default to both only when the user does not specify a type.
3. Open ChatGPT **Settings → Billing** and wait until **Transaction history**
   is populated. Select the resolved transaction’s **Open invoice** entry. If
   the click does not open a new tab, read that link’s visible `href`, open it
   in a new IAB tab, and verify the Stripe page shows the matching payment date
   and invoice number.
4. Capture each requested download with the event and click running together;
   a sequential click can navigate to a blocked file page before the event is
   captured:

   ```js
   const [download] = await Promise.all([
     tab.playwright.waitForEvent("download", { timeoutMs: 60000 }),
     tab.playwright.getByRole("button", {
       name: "Download receipt",
       exact: true,
     }).click(),
   ]);
   const downloadedPath = await download.path();
   ```

   Use **Download invoice** instead when the requested type is invoice. Repeat
   once for the other type only when both were requested.
5. Create `~/Downloads/chatgpt-fakturor` if needed and copy the requested PDFs
   there. Inspect existing files first and follow their naming convention.
   For the current folder, use:

   ```text
   YYYY-MM - Faktura, Jesper Liljegren.pdf
   YYYY-MM - Kvitto, Jesper Liljegren.pdf
   ```

   Add ` 2`, ` 3`, and so on before `.pdf` only when that month/document
   filename already exists. Do not put the invoice number in this convention.
6. Verify every requested destination file exists, is a PDF, contains the
   expected invoice number, and contains `Invoice` or `Receipt` as appropriate.
7. When email was requested, use the available email connector when it supports
   attachments. Otherwise prepare a browser draft with the exact recipient,
   a short subject and body, and the verified PDFs attached. Confirm the
   recipient, subject, and attachment names in the draft, then request the
   required action-time confirmation immediately before **Send**.

## Guardrails

- Keep the browser work in the Codex built-in browser; do not switch to Chrome
  or bypass a browser download block.
- Treat invoice URLs as sensitive account data: never print, log, paste, or
  include them in the final response.
- Do not change billing details, payment methods, subscriptions, or plan
  state.
- If a requested download or attachment fails, report the exact incomplete
  document and leave verified files or the prepared draft in place.

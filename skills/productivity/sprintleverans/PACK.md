# Pack layout

One pack per sprint, outside version control:
`~/.t3/userdata/sprintleverans-preparation/<YYYY-MM-DD>-sprint-<N>/`. The scripts read and write
these paths; keep the names exact.

```text
<pack>/
├── collect/            collect.py output: prs.json, sessions.json, images.json
├── manifest.json       selection, choices, authorization (you write)
├── orders/NN-slug/
│   ├── order.json      authored fields and images per FIELDS.md (you write)
│   ├── notes.md        evidence, caveats, open questions; never sent (you write)
│   └── execution/      per-step CLI responses (deliver.py)
├── images/             approved PNG/JPEG copies (you write)
├── readiness.json      environment, IDs, sprint, duplicates (deliver.py preflight)
├── ledger.json         every operation ID, before and after dispatch (deliver.py)
├── commands.txt        every CLI command run (deliver.py)
└── LEVERANS-<N>.md     presentation index (deliver.py verify)
```

## `manifest.json`

```json
{
  "sprint": 183,
  "period": { "from": "2026-10-28", "to": "2026-11-11" },
  "environment": "production",
  "requester": "Jesper Liljegren",
  "choices": { "requireCustomerAccept": false, "shouldBeInvoiced": false },
  "authorization": { "orderWrites": false, "instruction": null, "grantedAt": null },
  "items": [
    {
      "id": "S183-05",
      "directory": "orders/05-tags-rut",
      "group": "done",
      "selected": false,
      "stage": "developed",
      "existingOrderId": null
    }
  ]
}
```

- `group`: `done` (completed work) or `wip` (in progress, presented without an Order).
- `stage`: the terminal stage, one of `created`, `submitted`, `approved`, `in-sprint` or
  `developed`.
- `selected` and `authorization` change only on the user's word. Put their instruction, verbatim, in
  `authorization.instruction` and set `orderWrites: true`; `deliver.py run` refuses to write without
  it.
- `existingOrderId` set means deliver.py updates that Order instead of creating one.

# Order field template

How each Order field is written so the sprint presentation reads well. `deliver.py check` enforces
the mechanical rules marked ✓.

## How the fields render

Narrative fields are **Markdown**. Pass `--format markdown` on `order create` and `order update`.
The API converts the source to sanitized HTML for Present: use `-` lists, `[label](https://…)` links
and `**bold**`. Single line breaks are preserved. Images remain uploaded attachments. `title`,
`contacts`, `workOrderNumber` and `note` remain plain text.

The presentation page (`Order/Present`) shows **Lösning** alone, full width, in the largest font.
Every other field sits in a collapsed accordion below it. Lösning is the slide; the rest is detail
for anyone who opens it. Images attach after a field's text.

## Voice

Swedish, active voice, the user's outcome first. Name the user (personal, kund, utvecklare) and what
changed for them. Each field adds something new; a sentence appears in one field only ✓. Internal
tools may name the tool; product work avoids class names and jargon outside Implementationsdetaljer.

## Fields

### `title`: Titel

The outcome in at most 70 characters ✓, as a verb phrase or noun phrase. "Bevara RUT när fokus
lämnar kundtaggar", not "Fix blur handler".

### `solution`: Lösning (the slide)

```markdown
<En mening: vad som är nytt eller åtgärdat, och för vem.>

- <effekt för användaren>
- <effekt för användaren>
- <valfri tredje effekt>
```

At most 60 words ✓. No URLs ✓, PR numbers, verification or caveats; those belong in
Implementationsdetaljer. When the change is visible, attach the primary screenshot here
(`"field": "solution"`) so it appears on the slide.

### `purpose`, `customerNeed`, `howIsItSolvedToday`: goal, problem, workaround

Present asks three questions; answer each from the user's side in one sentence. All three are
required ✓.

| Field                | Question on the page                | Answers with                     |
| -------------------- | ----------------------------------- | -------------------------------- |
| `purpose`            | Vad vill kunden uppnå?              | the goal: "Att …"                |
| `customerNeed`       | Vad är kundens behov?               | the problem before the change    |
| `howIsItSolvedToday` | Hur jobbar/löser kunden detta idag? | the workaround before the change |

Leave `whereToSolve` and `contacts` empty; DEV-69 hides empty cards on Present.

### `suggestedSolution`: Lösningsförslag

```markdown
Omfattning:

- <vad leveransen omfattar>
- <…>

Utanför:

- <medvetet avgränsat, eller utelämna blocket>
```

### `implementationDetails`: Implementationsdetaljer

```markdown
Så fungerar det:

- <teknisk punkt>
- <teknisk punkt>

Så används det: <kommando eller klickväg, 1–3 rader, indraget två mellanslag>

Verifiering:

- <hur det verifierades och var: test, miljö, granskning>

Status:

- <Sammanfogad i master ÅÅÅÅ-MM-DD> · <Driftsatt ÅÅÅÅ-MM-DD | Ej driftsatt än>

Källor:

- [PR <nr> – <repo>](url)
```

Leave out **Så används det** when there is nothing to run or click. Every source is one bullet with
its URL ✓. Supporting screenshots attach here.

### `whereInSystem`: Var i systemet (optional)

A menu path for user-facing changes: `Kund › Redigera › Taggar`.

### `note`: Anteckning

One line ✓: `Sprint <N> · arbete <d mån>–<d mån ÅÅÅÅ>`. It stays on the Order permanently; keep
preparation instructions and caveats in the pack's `notes.md`.

## Images

PNG or JPEG, at most 20 MiB. Each image names its field and alt text (at most 500 characters ✓) that
states what it shows and how old it is. An image older than the change shows the earlier state and
says so in its alt text.

Present draws an image about 1200 px wide, so capture a crop of the relevant region at device scale
2: at least 1600 px wide and at most 1.25 times as tall as wide ✓. A full-page screenshot is scaled
down when it is taken and stays blurry however it is displayed. Open each image at 100% before using
it.

## Example

```json
{
  "title": "Bevara RUT när fokus lämnar kundtaggar",
  "solution": "Uppgifter som redan fyllts i ligger kvar när man går vidare från taggfältet.\n\n- RUT och intilliggande fält behåller sitt värde\n- Markören hamnar där man klickade\n- Endast taggarnas sökfält töms",
  "purpose": "Att uppgifter i kundformuläret ligger kvar när man byter fält.",
  "customerNeed": "Personal som gick direkt från taggar till RUT förlorade det de nyss skrivit.",
  "howIsItSolvedToday": "De fyllde i RUT och intilliggande fält en gång till.",
  "suggestedSolution": "Omfattning:\n- Enkel- och flervalsväljare för kundtaggar\n- Fokusbyte med tabb och klick",
  "implementationDetails": "Så fungerar det:\n- Blur-hanteringen återställer bara komponentens eget sökfält\n- Destinationsfältets värde och fokus lämnas orörda\n\nVerifiering:\n- Komponenttester för enkel- och flerval\n\nStatus:\n- Sammanfogad i master 2026-11-04 · Driftsatt 2026-11-05\n\nKällor:\n- [PR 5674 – Tengella_bare](https://dev.azure.com/tengella/Tengella/_git/Tengella_bare/pullrequest/5674)",
  "whereInSystem": "Kund › Redigera › Taggar",
  "note": "Sprint 183 · arbete 28 okt–11 nov 2026",
  "images": [
    {
      "path": "images/taggar-rut.png",
      "field": "solution",
      "alt": "Kundformulär där RUT behåller sitt värde efter fokusbyte från taggar, november 2026."
    }
  ]
}
```

import unittest

from check_body import check

GOOD = """**Solves:** saves are slow · DEV-42

## Summary

```text
on(save)
  if content is unchanged
    return <cached result>
```

## Evidence

**Verdict:** PASS+NOTES

- **Before:** 3.2 s **After:** 0.4 s

## Merge Danger

**Door:** two-way

**Blast Radius:** small

**Risk call:** safe to merge without review: one cached read, covered by the journey
"""


class CheckBodyTests(unittest.TestCase):
    def test_filled_body_passes(self):
        self.assertEqual(check(GOOD, "azure", draft=False), ([], []))

    def test_draft_allows_empty_verdict_but_final_does_not(self):
        body = GOOD.replace("**Verdict:** PASS+NOTES", "**Verdict:**")
        self.assertEqual(check(body, "azure", draft=True)[0], [])
        self.assertIn("verdict is not", check(body, "azure", draft=False)[0][0])

    def test_missing_section_and_placeholder_fail(self):
        body = GOOD.replace("## Merge Danger\n", "").replace("small", "<one-word description>")
        errors, _ = check(body, "azure", draft=False)
        self.assertIn("missing a '## Merge Danger' section", errors)
        self.assertIn("unfilled placeholder <one-word description>", errors)

    def test_placeholder_inside_code_is_ignored(self):
        self.assertNotIn("cached result", " ".join(check(GOOD, "azure", draft=False)[0]))

    def test_azure_length_limit(self):
        body = GOOD + "x" * 4000
        self.assertTrue(any("over the azure limit" in e for e in check(body, "azure", draft=False)[0]))
        self.assertEqual(check(body, "github", draft=False)[0], [])

    def test_warnings_do_not_fail(self):
        body = GOOD + "\nDetails: /tmp/dev71/REPORT.md. All tests pass.\n"
        errors, warnings = check(body, "azure", draft=False)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 2)

    def test_images_must_link_to_their_original(self):
        body = GOOD + (
            "\n![bare](https://x/a.png)\n"
            "[![linked](https://x/b.png)](https://x/b.png)\n"
            "[![elsewhere](https://x/c.png)](https://x/other)\n"
            "![clip](https://x/flow.mp4)\n"
        )
        warnings = check(body, "azure", draft=False)[1]
        self.assertEqual(
            warnings,
            [
                "image is not linked to its original, so it cannot be opened full size: https://x/a.png",
                "image links somewhere other than its original: https://x/c.png",
            ],
        )
        self.assertEqual(check(body, "github", draft=False)[1], [])

    def test_mermaid_block_fails_on_azure_only(self):
        body = GOOD + "\n```mermaid\ngraph LR\n  a --> b\n```\n"
        self.assertTrue(any("Mermaid" in e for e in check(body, "azure", draft=False)[0]))
        self.assertEqual(check(body, "github", draft=False)[0], [])


if __name__ == "__main__":
    unittest.main()

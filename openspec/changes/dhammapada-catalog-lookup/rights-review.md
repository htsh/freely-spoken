## Rights and source review (tasks 1.1–1.3)

This document closes the section 1 blocking gate for `dhammapada-catalog-lookup`. It records the canonical Dhammapada translation, its license posture, and the provenance metadata that every catalog row will carry.

## 1.1 Canonical translation

- **Translator:** F. Max Müller (1823–1900)
- **Edition:** *The Dhammapada*, in *The Sacred Books of the East*, Vol. X, Part I. Edited by F. Max Müller. Oxford: Clarendon Press, 1881.
- **Source URL:** `https://www.gutenberg.org/files/2017/2017-h/2017-h.htm` (Project Gutenberg ebook #2017).
- **Why Müller:** unambiguous public-domain posture is the deciding factor for v1. Buddharakkhita (BPS), Thanissaro (Access to Insight, typically CC BY-NC), Fronsdal, and Easwaran all introduce non-trivial license review for an app distributed through the App Store. Müller's Victorian English reads dated, which makes "gentle" matching harder — that risk is acknowledged and managed by the tone metadata, crisis-flag hard exclusion, and fixture review (tasks 2.4, 4.6, 7.x).
- **Revisit trigger:** if fixture lookup review (tasks 7.1–7.2) shows systematic tone mismatch that the metadata cannot recover, reopen the translation decision before release. Switching translator after labeling invalidates tone judgments, so the revisit must happen before the full labeling run (task 2.6).

## 1.2 License verification

What Project Gutenberg itself asserts and what we determine are two different things; this section keeps them separate.

- **What Project Gutenberg asserts:** the ebook #2017 page states only *"Public domain in the USA."* PG verifies US status; it does not make a worldwide claim. PG also notes the original introduction, notes, and index were omitted from the transcription — so the source is clean verse text, not Müller's commentary.
- **Our determination — authorial copyright (worldwide):** F. Max Müller died in 1900. Copyright in his translation (a derivative work; the translator holds it) expired under every term regime that matters: life+70 lapsed in 1970, life+100 in 2000. No surviving authorial copyright remains in any jurisdiction the App Store distributes to.
- **Our determination — US status and URAA:** the 1881 Oxford edition is pre-1929, so it is public domain in the US on the published-before-1929 rule. URAA copyright restoration does not apply: restoration only reaches foreign works still under copyright in their source country on the URAA date (Jan 1, 1996), and this work's UK source-country term (life+70) had already expired in 1970. It was therefore never restored.
- **Project Gutenberg trademark/header:** the app ships only canonical verse text extracted from the edition, never the Gutenberg header or trademark notice, keeping the app outside the scope of the Project Gutenberg License. The Gutenberg URL is recorded as the *source of the digital text we transcribed from*, not as a license dependency.
- **App-store compatibility:** no commercial or non-commercial restriction applies. The translation can be displayed in a paid or free app on any platform.
- **Conclusion:** public domain worldwide on the merits (author d. 1900). PG's narrower "USA" assertion is not a contradiction — it is the limit of what PG verifies, not a ceiling on the work's actual status. No license note required beyond provenance.

## 1.3 Per-row provenance metadata

Every Dhammapada catalog row SHALL carry these fields (matches the schema in task 2.1):

```json
{
  "translator": "F. Max Müller",
  "sourceUrl": "https://www.gutenberg.org/files/2017/2017-h/2017-h.htm",
  "publicDomainStatus": "public-domain-worldwide",
  "licenseNote": "F. Max Müller (d. 1900), The Dhammapada, Sacred Books of the East Vol. X Part I, Oxford 1881. Public domain worldwide. Digital text transcribed from Project Gutenberg ebook #2017; no Project Gutenberg header or trademark text is redistributed."
}
```

Tasks 1.1, 1.2, and 1.3 are closed by this document. Task 1.4 (seed all 423 vs curated subset) is resolved separately in `design.md` → "Resolved decisions": seed the full 423 from day one. The section 1 gate is fully closed.

## Verification log

- 2026-05-28 — confirmed `gutenberg.org/ebooks/2017` is *Dhammapada, a Collection of Verses … Translated by F. Max Müller*, from *Sacred Books of the East* Vol. X Part I; PG status line reads "Public domain in the USA"; introduction/notes/index omitted from the transcription.

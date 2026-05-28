## Rights and source review (tasks 1.1–1.3)

This document closes the section 1 blocking gate for `dhammapada-catalog-lookup`. It records the canonical Dhammapada translation, its license posture, and the provenance metadata that every catalog row will carry.

## 1.1 Canonical translation

- **Translator:** F. Max Müller (1823–1900)
- **Edition:** *The Dhammapada*, in *The Sacred Books of the East*, Vol. X, Part I. Edited by F. Max Müller. Oxford: Clarendon Press, 1881.
- **Source URL:** `https://www.gutenberg.org/files/2017/2017-h/2017-h.htm` (Project Gutenberg ebook #2017).
- **Why Müller:** unambiguous public-domain posture is the deciding factor for v1. Buddharakkhita (BPS), Thanissaro (Access to Insight, typically CC BY-NC), Fronsdal, and Easwaran all introduce non-trivial license review for an app distributed through the App Store. Müller's Victorian English reads dated, which makes "gentle" matching harder — that risk is acknowledged and managed by the tone metadata, crisis-flag hard exclusion, and fixture review (tasks 2.4, 4.6, 7.x).
- **Revisit trigger:** if fixture lookup review (tasks 7.1–7.2) shows systematic tone mismatch that the metadata cannot recover, reopen the translation decision before release. Switching translator after labeling invalidates tone judgments, so the revisit must happen before the full labeling run (task 2.6).

## 1.2 License verification

- **Authorial copyright:** F. Max Müller died in 1900. His translation entered the public domain worldwide under life+70 and life+100 regimes decades ago. There is no surviving authorial copyright in any jurisdiction the App Store distributes to.
- **Edition copyright:** the 1881 Oxford edition is pre-1929 and pre-URAA-restoration. It is in the public domain in the United States and in every country that observes a publication-based or life+70/100 term for foreign works of that era.
- **Project Gutenberg terms:** the underlying work is public domain. Project Gutenberg's added trademark/header text is not redistributed: the app ships only the canonical verse text extracted from the edition, not the Gutenberg header or trademark notice. This keeps the app outside the scope of the Project Gutenberg License entirely. The Gutenberg URL is recorded as the *source of the digital text we transcribed from*, not as a license dependency.
- **App-store compatibility:** no commercial or non-commercial restriction applies. The translation can be displayed in a paid or free app on any platform.
- **Conclusion:** public domain, worldwide. No license note required beyond provenance.

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

Tasks 1.1, 1.2, and 1.3 are closed by this document. Task 1.4 (seed all 423 vs curated subset) remains open and is the last gate before section 2 work begins.

# Benchmark protocol

## Revision history

- `questions_v1.json`: 20 questions, 15 dev / 5 test. The first fixed-window A/B/C run and its test results were inspected. This version is retained as provenance and is **not** an independent held-out test for the final strategies.
- `questions.json` (v2): written before the first run with fixed A and sentence-grouped B/C. Questions q01–q20 are dev, including the five formerly tested questions. Questions q21–q25 are a new held-out test set. Questions q26–q27 add conditional/exception cases on dev. The missing alternative evidence for q17 was added only after v1 inspection and remains dev.
- Frozen v2 SHA-256: `30d0cfd3c2f0e79cc442d685382aa082034c626c1e2d926a3dadf1ac9e0e6619`.

## Construction and checks

All questions were drafted from the local 2020 Taiwan Tourism Guide Book before their corresponding retrieval run. Each gold quote was matched to the extracted physical PDF page. The source ID, page, expected answer, and quote were reviewed against the page text. Filters are provided by the wording "in the ... section" and use `category` values from `manifest.json`; they do not include the gold source or answer.

Version 2 has 27 questions: 22 dev, 5 test. There are direct, paraphrase, conditional, exception, and filter questions. Eight questions have a filter, including four on test. The five test questions cover overview, transport, festivals, souvenirs, and outlying islands. Dev and test share one PDF, and q23/test and q05/dev both use physical page 10 but ask about different festivals. This creates a page-level leakage risk that the report must disclose. No further strategy or gold changes should be made using the v2 test scores; if changes are necessary, create a new test split and preserve this file.

The strict automatic metric requires a retrieved chunk on a listed gold page that contains the full quote. Manual grounding review may identify equivalent evidence on another page; such cases must be recorded without silently changing the frozen gold or claiming an improved held-out score.

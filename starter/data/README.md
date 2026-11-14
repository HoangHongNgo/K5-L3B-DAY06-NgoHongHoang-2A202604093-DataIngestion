# Input format

Put PDFs in this directory and create `manifest.json`. Paths are relative to the
manifest file. Use real, licensed documents; the example below is a format guide,
not a completed corpus.

```json
{
  "documents": [
    {
      "document_id": "handbook-2025",
      "path": "handbook.pdf",
      "source": "handbook.pdf",
      "title": "Student handbook",
      "category": "handbook",
      "year": 2025,
      "language": "en",
      "license_or_permission": "Describe the actual permission here",
      "content_pages": [3, 4, 5]
    }
  ]
}
```

`content_pages` is optional; when provided, only listed physical PDF pages are
indexed. Pages with no extractable text require OCR or a different source. Record
page selection and license accurately. `category`, `year`, and `language` can be
used as query filters; only provide values verified from the source.

For a single book with distinct parts, `section_ranges` may assign a page-level
`category`, for example
`[{"start_page": 7, "end_page": 13, "category": "festivals"}]`.
Ranges must not overlap; pages outside the ranges use the document category.

For evaluation, create `questions.json` with a `questions` array. Each item needs
`id`, `split` (`dev` or `test`), `question`, `expected_answer`,
`gold_source_id`, `gold_page`, and `evidence_quote`. Optional `filter` is an
object such as `{"category": "handbook"}`. For multiple valid evidence spans,
use `gold_evidence` instead of the three single-gold fields:

```json
{
  "questions": [
    {
      "id": "q01",
      "split": "dev",
      "question": "What is the deadline?",
      "expected_answer": "The stated deadline",
      "gold_evidence": [
        {"source_id": "handbook-2025", "page": 3, "evidence_quote": "Exact quote from page 3"}
      ],
      "filter": {"category": "handbook"}
    }
  ]
}
```

The pipeline checks that gold quotes occur on the named page before retrieval.
Write and freeze the benchmark before inspecting test results.

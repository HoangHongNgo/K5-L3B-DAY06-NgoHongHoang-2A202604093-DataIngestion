"""Automatic evidence retrieval checks; manual rubric items stay manual."""
from typing import Any

from .ingestion import evidence_text
from .models import DocumentPage


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Accept any listed gold evidence on its documented document and page."""
    gold = question.get("gold_evidence") or [{
        "source_id": question["gold_source_id"],
        "page": question["gold_page"],
        "evidence_quote": question["evidence_quote"],
    }]
    matches = []
    for hit in hits:
        hit_text = evidence_text(hit["text"])
        matched = any(
            hit["document_id"] == item["source_id"]
            and hit["page"] == item["page"]
            and evidence_text(item["evidence_quote"]) in hit_text
            for item in gold
        )
        matches.append(matched)
    return {
        "id": question["id"], "split": question["split"],
        "question": question["question"], "expected_answer": question["expected_answer"],
        "gold_evidence": gold, "filter": question.get("filter"),
        "hits": [{**hit, "evidence_match": match} for hit, match in zip(hits, matches)],
        "hit_at_1": bool(matches and matches[0]),
        "evidence_hit_at_3": any(matches[:3]),
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for trace in traces:
        strategy = trace["strategy"]
        split = trace["split"]
        bucket = result.setdefault(strategy, {}).setdefault(split, {
            "questions": 0, "hit_at_1": 0, "evidence_hit_at_3": 0,
        })
        bucket["questions"] += 1
        bucket["hit_at_1"] += int(trace["hit_at_1"])
        bucket["evidence_hit_at_3"] += int(trace["evidence_hit_at_3"])
    return result


def audit_metadata(traces: list[dict[str, Any]], pages: list[DocumentPage]) -> dict[str, Any]:
    """Check trace metadata and text spans against the extracted source pages."""
    lookup = {(page.document_id, page.page): page for page in pages}
    checks = []
    filters = []
    for trace in traces:
        for rank, hit in enumerate(trace["hits"], start=1):
            page = lookup.get((hit["document_id"], hit["page"]))
            meta = hit["metadata"]
            start, end = meta.get("start_char"), meta.get("end_char")
            correct = bool(
                page is not None and hit["source"] == page.source
                and isinstance(start, int) and isinstance(end, int)
                and 0 <= start < end <= len(page.text)
                and page.text[start:end].strip() == hit["text"]
                and all(meta.get(key) == value for key, value in page.metadata.items())
            )
            checks.append({"strategy": trace["strategy"], "split": trace["split"],
                           "question_id": trace["id"], "rank": rank, "correct": correct})
        if trace["strategy"] == "C" and trace.get("filter"):
            compliant = bool(trace["hits"]) and all(
                all(str(hit.get(key, hit["metadata"].get(key))) == str(value)
                    for key, value in trace["filter"].items())
                for hit in trace["hits"]
            )
            filters.append({"question_id": trace["id"], "split": trace["split"],
                            "compliant": compliant})
    test_checks = [item for item in checks if item["split"] == "test"]
    return {
        "method": "Programmatic comparison of retrieved hits with extracted PDF pages and manifest metadata; not a human audit.",
        "test_top3_correct": sum(item["correct"] for item in test_checks),
        "test_top3_total": len(test_checks),
        "all_top3_correct": sum(item["correct"] for item in checks),
        "all_top3_total": len(checks),
        "filter_compliant_questions": sum(item["compliant"] for item in filters),
        "filter_questions": len(filters),
        "filter_details": filters,
        "failures": [item for item in checks if not item["correct"]],
    }

"""Run two chunking methods, exact vector retrieval, and evidence checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
import warnings

from dotenv import load_dotenv

from .chunking import by_sentence, fixed_size
from .embeddings import MyEmbedder
from .evaluation import audit_metadata, evaluate_query, summarize
from .ingestion import evidence_text, load_pdf
from .store import PgVectorStore


STARTER = Path(__file__).resolve().parents[1]
STRATEGIES = {
    "A": {"method": "fixed", "size": 450, "overlap": 45},
    "B": {"method": "sentence_group", "size": 650, "overlap": 0},
    "C": {"method": "sentence_group", "size": 650, "overlap": 0},
}


def _read_json(path: Path, key: str) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}; see starter/data/README.md")
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data[key] if isinstance(data, dict) else data
    if not isinstance(values, list):
        raise ValueError(f"{path}: expected an array or object with '{key}' array")
    return values


def _load_corpus(manifest: Path):
    documents = _read_json(manifest, "documents")
    if not documents:
        raise ValueError("Manifest has no documents")
    pages = []
    seen_ids = set()
    for doc in documents:
        for field in ("document_id", "path", "source", "license_or_permission", "category"):
            if not doc.get(field):
                raise ValueError(f"Manifest document missing {field}: {doc}")
        if doc["document_id"] in seen_ids:
            raise ValueError(f"Duplicate document_id: {doc['document_id']}")
        seen_ids.add(doc["document_id"])
        path = (manifest.parent / doc["path"]).resolve()
        if path.suffix.lower() != ".pdf" or not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")
        if doc.get("sha256"):
            with path.open("rb") as stream:
                actual_hash = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual_hash != doc["sha256"]:
                raise ValueError(f"PDF checksum differs from manifest: {path}")
        selected = set(doc["content_pages"]) if "content_pages" in doc else None
        if selected is not None and (not selected or any(not isinstance(n, int) or n < 1 for n in selected)):
            raise ValueError(f"Invalid content_pages for {doc['document_id']}")
        extracted = load_pdf(path, doc["document_id"], doc["source"], selected)
        found = {page.page for page in extracted}
        if selected is not None and not selected <= found:
            raise ValueError(f"{path}: content_pages without extractable text: {sorted(selected - found)}")
        page_categories = {}
        for section in doc.get("section_ranges", []):
            start = section["start_page"]
            end = section["end_page"]
            category = section["category"]
            if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start or not category:
                raise ValueError(f"Invalid section range: {section}")
            for number in range(start, end + 1):
                if number in page_categories:
                    raise ValueError(f"Overlapping section ranges at page {number}")
                page_categories[number] = category
        for page in extracted:
            expected_chars = doc.get("page_character_counts", {}).get(str(page.page))
            if expected_chars is not None and len(page.text) != expected_chars:
                raise ValueError(f"Page {page.page} text differs from manifest: {path}")
            page.metadata = {key: doc[key] for key in
                             ("category", "year", "language", "title", "license_or_permission")
                             if key in doc}
            page.metadata["category"] = page_categories.get(page.page, doc["category"])
            pages.append(page)
    if not pages:
        raise ValueError("No pages with extractable content")
    if len(pages) < 30:
        warnings.warn(f"Only {len(pages)} content pages; assignment requires at least 30", stacklevel=2)
    return pages


def _load_questions(path: Path, pages) -> list[dict]:
    questions = _read_json(path, "questions")
    lookup = {(page.document_id, page.page): evidence_text(page.text) for page in pages}
    seen = set()
    for question in questions:
        for field in ("id", "split", "question", "expected_answer"):
            if not question.get(field):
                raise ValueError(f"Question missing {field}: {question}")
        if question["id"] in seen or question["split"] not in {"dev", "test"}:
            raise ValueError(f"Duplicate ID or invalid split: {question['id']}")
        seen.add(question["id"])
        gold = question.get("gold_evidence") or [{
            "source_id": question.get("gold_source_id"), "page": question.get("gold_page"),
            "evidence_quote": question.get("evidence_quote"),
        }]
        for item in gold:
            text = lookup.get((item.get("source_id"), item.get("page")), "")
            quote = item.get("evidence_quote")
            if not quote or evidence_text(quote) not in text:
                raise ValueError(f"Gold evidence not found in source page: {question['id']}")
        if "filter" in question and not isinstance(question["filter"], dict):
            raise ValueError(f"Filter must be an object: {question['id']}")
    if len(questions) < 20:
        warnings.warn(f"Only {len(questions)} questions; assignment requires at least 20", stacklevel=2)
    return questions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=STARTER / "data/manifest.json")
    parser.add_argument("--questions", type=Path, default=STARTER / "data/questions.json")
    parser.add_argument("--results", type=Path, default=STARTER / "results")
    parser.add_argument("--ingest-only", action="store_true")
    args = parser.parse_args()

    start_time = perf_counter()
    load_dotenv(STARTER / ".env")
    os.environ.setdefault("HF_HOME", str(STARTER.parent / ".local/models/huggingface"))
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is missing; copy .env.example to starter/.env and configure PostgreSQL")
    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    pages = _load_corpus(args.manifest)
    questions = [] if args.ingest_only else _load_questions(args.questions, pages)
    embedder = MyEmbedder(model_name)
    store = PgVectorStore(database_url, embedder.dimensions, model_name)
    store.create_schema()
    stats = {}
    chunks_by_strategy = {}
    for strategy in ("A", "B", "C"):
        if strategy == "C":
            chunks, vectors = chunks_by_strategy["B"]
        else:
            config = STRATEGIES[strategy]
            if config["method"] == "fixed":
                chunks = [chunk for page in pages for chunk in
                          fixed_size(page, config["size"], config["overlap"])]
            else:
                chunks = [chunk for page in pages for chunk in
                          by_sentence(page, config["size"])]
            vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        store.upsert(strategy, chunks, vectors)
        chunks_by_strategy[strategy] = (chunks, vectors)
        total_characters = sum(len(c.text) for c in chunks)
        stats[strategy] = {"method": STRATEGIES[strategy]["method"],
                           "size": STRATEGIES[strategy]["size"],
                           "overlap": STRATEGIES[strategy]["overlap"],
                           "chunks": len(chunks), "characters": total_characters,
                           "mean_chunk_chars": round(total_characters / len(chunks), 1) if chunks else 0,
                           "min_chunk_chars": min(map(lambda c: len(c.text), chunks), default=0),
                           "max_chunk_chars": max(map(lambda c: len(c.text), chunks), default=0)}
        print(f"{strategy}: indexed {len(chunks)} chunks")

    ingest_seconds = round(perf_counter() - start_time, 3)
    traces = []
    if questions:
        query_vectors = {question["id"]: embedder.embed_query(question["question"])
                         for question in questions}
        for strategy in STRATEGIES:
            for question in questions:
                filters = question.get("filter") if strategy == "C" else None
                hits = store.search(strategy, query_vectors[question["id"]], 3, filters)
                traces.append({"strategy": strategy, **evaluate_query(question, hits)})
    args.results.mkdir(parents=True, exist_ok=True)
    (args.results / "traces.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    public_traces = []
    for trace in traces:
        public_traces.append({
            "strategy": trace["strategy"], "id": trace["id"], "split": trace["split"],
            "question": trace["question"], "filter": trace["filter"],
            "hit_at_1": trace["hit_at_1"],
            "evidence_hit_at_3": trace["evidence_hit_at_3"],
            "hits": [{**{key: value for key, value in hit.items() if key != "text"},
                      "text_sha256": hashlib.sha256(hit["text"].encode("utf-8")).hexdigest(),
                      "text_length": len(hit["text"])} for hit in trace["hits"]],
        })
    (args.results / "traces_public.json").write_text(
        json.dumps(public_traces, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata_report = audit_metadata(traces, pages)
    (args.results / "metadata_audit.json").write_text(
        json.dumps(metadata_report, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"model": model_name, "dimensions": embedder.dimensions,
              "distance": "exact cosine", "content_pages": len(pages),
              "ingest_seconds": ingest_seconds,
              "total_seconds": round(perf_counter() - start_time, 3),
              "texts_truncated_by_model": embedder.truncated_text_count,
              "strategies": stats, "retrieval": summarize(traces)}
    (args.results / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.results / 'summary.json'} and traces.json")


if __name__ == "__main__":
    main()

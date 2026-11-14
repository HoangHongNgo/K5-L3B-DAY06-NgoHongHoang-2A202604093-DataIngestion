"""Validate assignment benchmark counts, gold evidence and filter metadata."""
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run import STARTER, _load_corpus, _load_questions


def main() -> None:
    pages = _load_corpus(STARTER / "data/manifest.json")
    questions = _load_questions(STARTER / "data/questions.json", pages)
    splits = Counter(question["split"] for question in questions)
    types = Counter(question.get("type", "unspecified") for question in questions)
    filtered = [question for question in questions if question.get("filter")]
    if len(questions) < 20 or splits["dev"] < 15 or splits["test"] < 5:
        raise ValueError("Need at least 20 questions, 15 dev and 5 test")
    if len(filtered) < 3 or not any(q["split"] == "test" for q in filtered):
        raise ValueError("Need at least three filter questions, including one on test")
    lookup = {(page.document_id, page.page): page for page in pages}
    for question in filtered:
        gold = question.get("gold_evidence") or [{
            "source_id": question["gold_source_id"], "page": question["gold_page"]
        }]
        if not any(all(lookup[(item["source_id"], item["page"])].metadata.get(key) == value
                       for key, value in question["filter"].items()) for item in gold):
            raise ValueError(f"Filter excludes all gold pages: {question['id']}")
    print(f"Content pages: {len(pages)}")
    print(f"Questions: {len(questions)} | dev: {splits['dev']} | test: {splits['test']}")
    print(f"Filtered questions: {len(filtered)} | test: {sum(q['split'] == 'test' for q in filtered)}")
    print(f"Question types: {dict(types)}")
    print("Gold quotes and filter values verified against the extracted PDF pages.")


if __name__ == "__main__":
    main()

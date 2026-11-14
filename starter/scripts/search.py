"""Search indexed PDF chunks with the same model and pgvector store as the benchmark."""
import argparse
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

STARTER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STARTER))

from src.embeddings import MyEmbedder
from src.store import PgVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Question to search; omit for interactive mode")
    parser.add_argument("--strategy", choices=("A", "B", "C"), default="C")
    parser.add_argument("--category", help="Section filter for strategy C, e.g. festivals")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if args.category and args.strategy != "C":
        parser.error("--category is available only with strategy C")
    if args.top_k < 1:
        parser.error("--top-k must be positive")

    load_dotenv(STARTER / ".env")
    os.environ.setdefault("HF_HOME", str(STARTER.parent / ".local/models/huggingface"))
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL missing; run scripts/local_db.ps1 or configure starter/.env")
    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedder = MyEmbedder(model_name)
    store = PgVectorStore(database_url, embedder.dimensions, model_name)
    filters = {"category": args.category} if args.category else None

    def search(question: str) -> None:
        hits = store.search(args.strategy, embedder.embed_query(question), args.top_k, filters)
        if not hits:
            print("No indexed chunks found. Run 'python -m src.run' from starter/ first.")
            return
        for rank, hit in enumerate(hits, 1):
            print(f"\n[{rank}] score={hit['score']:.4f} | page={hit['page']} "
                  f"| category={hit['metadata'].get('category')} | source={hit['source']}")
            print(hit["text"])

    if args.question:
        search(args.question)
    else:
        print("Enter a question (empty line to quit).")
        while True:
            try:
                question = input("\nQuestion> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not question:
                break
            search(question)


if __name__ == "__main__":
    main()

"""
Ingest All — Full Knowledge Base Builder
------------------------------------------
Reads all processed JSON files, generates embeddings using
nomic-embed-text (via Ollama), and uploads everything to Qdrant.

Usage:
    python app/ingest_all.py            # Add to existing collection
    python app/ingest_all.py --recreate # Delete and rebuild from scratch
"""

import json
import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "embeddings"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vectorstore"))

from embedder import generate_embeddings_batch
from qdrant_store import get_client, create_collection, upload_chunks


# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed_documents")


def load_all_chunks():
    """Load all chunks from JSON files in processed_documents/."""
    all_chunks = []

    for filename in sorted(os.listdir(PROCESSED_DIR)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(PROCESSED_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        chunks = data["chunks"]
        all_chunks.extend(chunks)
        print(f"  Loaded {len(chunks):4d} chunks from {filename}")

    return all_chunks


def main():
    recreate = "--recreate" in sys.argv

    print("=" * 60)
    print("RFP Sentinel — Knowledge Base Builder")
    print("=" * 60)

    # Step 1: Load all processed chunks
    print("\n[1/3] Loading processed chunks...")
    chunks = load_all_chunks()
    print(f"      Total: {len(chunks)} chunks\n")

    if not chunks:
        print("No chunks found. Run the ingestion pipeline first:")
        print("  python app/ingestion/pipeline.py")
        sys.exit(1)

    # Step 2: Generate embeddings
    print("[2/3] Generating embeddings (nomic-embed-text via Ollama)...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = generate_embeddings_batch(texts)
    print(f"      ✓ Generated {len(embeddings)} embeddings\n")

    # Step 3: Upload to Qdrant
    print("[3/3] Uploading to Qdrant...")
    client = get_client()
    create_collection(client, recreate=recreate)
    upload_chunks(chunks, embeddings, client)

    # Final stats
    collection_info = client.get_collection("rfp_knowledge_base")
    print(f"\n{'=' * 60}")
    print(f"DONE — Knowledge base ready!")
    print(f"  Collection: rfp_knowledge_base")
    print(f"  Total points: {collection_info.points_count}")
    print(f"  Vector size: {collection_info.config.params.vectors.size}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

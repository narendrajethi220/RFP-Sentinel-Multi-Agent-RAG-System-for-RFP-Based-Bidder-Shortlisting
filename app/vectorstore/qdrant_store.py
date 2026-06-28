"""
Qdrant Vector Store
---------------------
Handles creating collections and uploading chunk embeddings
to the Qdrant vector database.

Qdrant runs as a Docker container (rfp-sentinal-qdb) on port 6333.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)


import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "rfp_knowledge_base")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))


def get_client():
    """Create and return a Qdrant client."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def create_collection(client=None, recreate=False):
    """
    Create the knowledge base collection in Qdrant.

    Args:
        client: QdrantClient instance (creates one if not provided)
        recreate: If True, delete and recreate the collection

    Returns:
        QdrantClient instance
    """
    if client is None:
        client = get_client()

    # Check if collection exists
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in collections:
        if recreate:
            print(f"  Deleting existing collection '{COLLECTION_NAME}'...")
            client.delete_collection(COLLECTION_NAME)
        else:
            print(f"  Collection '{COLLECTION_NAME}' already exists ({client.get_collection(COLLECTION_NAME).points_count} points)")
            return client

    print(f"  Creating collection '{COLLECTION_NAME}' (dim={EMBEDDING_DIM})...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE,
        ),
    )
    print(f"  ✓ Collection created")

    return client


def upload_chunks(chunks, embeddings, client=None):
    """
    Upload chunks with their embeddings to Qdrant.

    Each chunk becomes a "point" in Qdrant with:
      - id: sequential integer
      - vector: the 768-dim embedding
      - payload: chunk text + all metadata

    Args:
        chunks: List of chunk dicts (from pipeline.py output)
        embeddings: List of embedding vectors (same order as chunks)
        client: QdrantClient instance
    """
    if client is None:
        client = get_client()

    points = []

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        point = PointStruct(
            id=i + 1,
            vector=embedding,
            payload={
                "text": chunk["text"],
                "chunk_id": chunk["chunk_id"],
                "document_source": chunk["metadata"]["document_source"],
                "document_category": chunk["metadata"]["document_category"],
                "section_id": chunk["metadata"]["section_id"],
                "section_heading": chunk["metadata"]["section_heading"],
                "page_numbers": chunk["metadata"]["page_numbers"],
                "chunk_index": chunk["metadata"]["chunk_index"],
                "total_chunks": chunk["metadata"]["total_chunks"],
            },
        )
        points.append(point)

    # Upload in batches of 100
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        done = min(i + batch_size, len(points))
        print(f"  Uploaded {done}/{len(points)} points to Qdrant")

    print(f"  ✓ All {len(points)} points uploaded")

"""
Embedding Generator
--------------------
Generates vector embeddings for document chunks using
Nomic Embed Text via Ollama (runs locally).

Model: nomic-embed-text (768 dimensions)
"""

import ollama
import os
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))


def generate_embedding(text):
    """
    Generate embedding for a single text string.

    Args:
        text: The text to embed

    Returns:
        List of floats (768-dimensional vector)
    """
    result = ollama.embed(model=EMBEDDING_MODEL, input=text)
    return result.embeddings[0]


def generate_embeddings_batch(texts, batch_size=25):
    """
    Generate embeddings for a list of texts in batches.
    Ollama supports passing multiple inputs at once.

    Args:
        texts: List of text strings
        batch_size: How many texts to embed per API call

    Returns:
        List of embedding vectors (each is a list of 768 floats)
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = ollama.embed(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend(result.embeddings)

        done = min(i + batch_size, len(texts))
        print(f"  Embedded {done}/{len(texts)} chunks")

    return all_embeddings

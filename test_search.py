import sys
import os
import textwrap

# Add app directories to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "app/embeddings")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "app/vectorstore")))

from embedder import generate_embedding
from qdrant_store import get_client, COLLECTION_NAME

def main():
    print("="*70)
    print("🔍 RFP Sentinel — Interactive Semantic Search Test")
    print("="*70)
    print("\nThis script will:")
    print("  1. Take your plain text question.")
    print("  2. Convert it into a 768-number array (an Embedding).")
    print("  3. Ask Qdrant to find the closest matching arrays in the database.")
    print("  4. Return the original text chunks for those arrays.\n")

    client = get_client()

    while True:
        try:
            query = input("\n🤔 Enter a question (or type 'quit' to exit):\n> ")
            if query.lower() in ['quit', 'q', 'exit']:
                break
            
            if not query.strip():
                continue

            print("\n⏳ Generating embedding for your question...")
            query_vector = generate_embedding(query)
            
            print(f"   ✓ Question converted to vector of length {len(query_vector)}")
            print(f"   ✓ First 3 numbers: {query_vector[:3]}...\n")

            print("🔎 Searching Qdrant Database for the top 3 closest matches...\n")
            
            hits = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=3,
            )

            for i, hit in enumerate(hits.points):
                # The score represents how close the two vectors are (Cosine Similarity). 1.0 is a perfect match.
                print(f"[{i+1}] MATCH SCORE: {hit.score:.4f} " + ("(High Confidence) 🟢" if hit.score > 0.7 else "(Moderate Confidence) 🟡"))
                print(f"    Source Document: {hit.payload['document_source']}")
                print(f"    Category: {hit.payload['document_category']}")
                print(f"    Section: {hit.payload['section_heading']}")
                print(f"    Pages: {hit.payload['page_numbers']}")
                print(f"    Text Preview:")
                
                # Print a nicely wrapped preview of the text
                preview = hit.payload['text'][:400].replace('\n', ' ') + "..."
                wrapped_text = textwrap.fill(preview, width=80, initial_indent="      ", subsequent_indent="      ")
                print(f"{wrapped_text}\n")
                print("-" * 70)

        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()

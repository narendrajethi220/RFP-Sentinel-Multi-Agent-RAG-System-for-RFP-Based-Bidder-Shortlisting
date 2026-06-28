"""
Ingestion Pipeline
-------------------
Orchestrates the full document ingestion flow:
  PDF → Clean → Extract Header → Parse Structure → Smart Chunk → Save JSON

Can process a single file or batch-process all files in data/raw_documents/.
"""

import json
import os
import sys

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_loader import PDFLoader
from text_cleaner import TextCleaner
from structure_parser import parse_structure
from smart_chunker import SmartChunker
from header_extractor import extract_header


# Resolve project root (2 levels up from app/ingestion/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DOCUMENTS_DIR = os.path.join(PROJECT_ROOT, "data", "raw_documents")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed_documents")


def process_single_file(file_path, output_dir=None):
    """
    Process a single PDF file through the full ingestion pipeline.
    
    Args:
        file_path: Path to the PDF file
        output_dir: Directory to save the JSON output (default: data/processed_documents/)
    
    Returns:
        List of chunk dicts
    """
    if output_dir is None:
        output_dir = PROCESSED_DIR

    filename = os.path.basename(file_path)
    print(f"\n{'='*60}")
    print(f"Processing: {filename}")
    print(f"{'='*60}")

    # Step 1: Load PDF
    print("  [1/5] Loading PDF...")
    loader = PDFLoader(file_path)
    pages = loader.load()
    print(f"         → {len(pages)} pages loaded")

    # Step 2: Clean text
    print("  [2/5] Cleaning text (stripping Hindi, normalizing)...")
    cleaner = TextCleaner()
    cleaned_pages, full_text = cleaner.clean_pages(pages)
    print(f"         → {len(cleaned_pages)} pages after cleaning, {len(full_text)} chars")

    # Step 3: Extract header metadata
    print("  [3/5] Extracting document header...")
    first_page = cleaned_pages[0]["text"] if cleaned_pages else ""
    header = extract_header(first_page, filename)
    print(f"         → Title: {header['document_title']}")
    print(f"         → Category: {header['document_category']}")
    print(f"         → Authority: {header['issuing_authority'] or 'N/A'}")

    # Step 4: Parse structure
    print("  [4/5] Parsing document structure...")
    units = parse_structure(full_text, cleaned_pages)
    print(f"         → {len(units)} structural units detected")

    # Step 5: Smart chunking
    print("  [5/5] Creating chunks...")
    chunker = SmartChunker()
    doc_metadata = {
        "document_source": filename,
        "document_category": header["document_category"],
        "document_title": header["document_title"],
        "issuing_authority": header["issuing_authority"],
    }
    chunks = chunker.chunk(units, doc_metadata)

    # Stats
    sizes = [len(c["text"]) for c in chunks]
    avg_size = sum(sizes) // len(sizes) if sizes else 0
    print(f"         → {len(chunks)} chunks (avg {avg_size} chars, "
          f"min {min(sizes)} max {max(sizes)})")

    # Save to JSON
    os.makedirs(output_dir, exist_ok=True)
    output_filename = filename.replace(".pdf", ".json").replace(" ", "_")
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "document_metadata": doc_metadata,
            "total_chunks": len(chunks),
            "chunks": chunks,
        }, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Saved to {output_path}")

    return chunks


def process_all(raw_dir=None, output_dir=None):
    """
    Batch-process all PDFs in the raw_documents directory.
    Walks through all subdirectories (gem/, bis/, enterprise/, etc.)
    """
    if raw_dir is None:
        raw_dir = RAW_DOCUMENTS_DIR
    if output_dir is None:
        output_dir = PROCESSED_DIR

    all_chunks = []
    file_count = 0

    for root, dirs, files in os.walk(raw_dir):
        for filename in sorted(files):
            if not filename.lower().endswith(".pdf"):
                continue

            file_path = os.path.join(root, filename)
            chunks = process_single_file(file_path, output_dir)
            all_chunks.extend(chunks)
            file_count += 1

    print(f"\n{'='*60}")
    print(f"DONE — Processed {file_count} documents → {len(all_chunks)} total chunks")
    print(f"Output saved to: {output_dir}/")
    print(f"{'='*60}")

    return all_chunks


# --- CLI Entry Point ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Process a specific file
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        process_single_file(file_path)
    else:
        # Process all documents
        process_all()
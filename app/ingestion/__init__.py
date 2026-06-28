"""
Ingestion Layer — Structure-Aware Document Processing
------------------------------------------------------
Modules:
  pdf_loader        — Extract raw text from PDFs
  text_cleaner      — Clean and normalize text
  structure_parser  — Detect document structure (sections, clauses)
  smart_chunker     — Structure-aware chunking
  header_extractor  — Extract document metadata from headers
  pipeline          — Orchestrate the full ingestion flow
"""

from .pdf_loader import PDFLoader
from .text_cleaner import TextCleaner
from .structure_parser import parse_structure
from .smart_chunker import SmartChunker
from .header_extractor import extract_header
from .pipeline import process_single_file, process_all

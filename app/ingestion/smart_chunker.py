"""
Smart Chunker for Government Documents
----------------------------------------
Creates chunks from structural units with these key rules:

1. NEVER let a chunk cross a section boundary
2. Small sections (< MAX_CHUNK_SIZE) → kept as one chunk
3. Large sections → split at paragraph boundaries, within that section only
4. Every chunk gets a context prefix (parent section heading)
   so the LLM always knows which section the chunk belongs to

This prevents the core problem: two different sections about
different topics getting merged into one chunk, causing LLM hallucination.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


# Chunking parameters
MAX_CHUNK_SIZE = 1200    # chars — large enough for verbose legal text
CHUNK_OVERLAP = 100      # overlap ONLY within the same section
MIN_CHUNK_SIZE = 50      # skip tiny fragments


class SmartChunker:

    def __init__(self, max_chunk_size=MAX_CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

        # Fallback splitter — used ONLY when a single section is too large
        # Splits at paragraph > newline > sentence > word boundaries
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
        )

    def chunk(self, structural_units, doc_metadata=None):
        """
        Convert structural units into final chunks with metadata.

        Args:
            structural_units: List of dicts from structure_parser.parse_structure()
            doc_metadata: Optional dict with document-level info like
                          {"document_source": "...", "document_category": "..."}

        Returns:
            List of chunk dicts:
            {
                "chunk_id": "doc_001_chunk_005",
                "text": "Section: 2.5 Earnest Money Deposit\n\nBidders must...",
                "metadata": {
                    "document_source": str,
                    "document_category": str,
                    "section_id": str,
                    "section_heading": str,
                    "page_numbers": [int],
                    "chunk_index": int,
                    "total_chunks": int,  # filled in at the end
                    "structural_level": int,
                }
            }
        """
        if doc_metadata is None:
            doc_metadata = {}

        raw_chunks = []

        for unit in structural_units:
            unit_text = unit["text"].strip()

            if len(unit_text) < MIN_CHUNK_SIZE:
                continue

            # Build the context prefix — this gets prepended to every chunk
            # so the LLM knows which section/clause it's reading
            context_prefix = self._build_context_prefix(unit)

            if len(unit_text) <= self.max_chunk_size:
                # Small enough → one chunk, no splitting needed
                raw_chunks.append(
                    self._make_chunk(
                        text=unit_text,
                        context_prefix=context_prefix,
                        unit=unit,
                        doc_metadata=doc_metadata,
                    )
                )
            else:
                # Too large → split within this section only
                sub_texts = self.fallback_splitter.split_text(unit_text)

                for sub_text in sub_texts:
                    if len(sub_text.strip()) < MIN_CHUNK_SIZE:
                        continue

                    raw_chunks.append(
                        self._make_chunk(
                            text=sub_text.strip(),
                            context_prefix=context_prefix,
                            unit=unit,
                            doc_metadata=doc_metadata,
                        )
                    )

        # Now assign chunk IDs and total_chunks
        doc_name = doc_metadata.get("document_source", "doc")
        # Clean filename for ID
        doc_prefix = doc_name.replace(".pdf", "").replace(" ", "_")[:30]

        for i, chunk in enumerate(raw_chunks):
            chunk["chunk_id"] = f"{doc_prefix}_chunk_{i+1:03d}"
            chunk["metadata"]["chunk_index"] = i + 1
            chunk["metadata"]["total_chunks"] = len(raw_chunks)

        return raw_chunks

    def _build_context_prefix(self, unit):
        """
        Build a context prefix string from the structural unit.
        Example: "Section 2.5: Earnest Money Deposit (EMD)"
        """
        section_id = unit.get("section_id", "")
        heading = unit.get("heading", "")
        level = unit.get("level", 0)

        if level == 0:
            return ""  # preamble, no prefix needed

        # Build prefix based on what we have
        parts = []

        if section_id and heading:
            parts.append(f"[Section {section_id}: {heading}]")
        elif section_id:
            parts.append(f"[Section {section_id}]")
        elif heading:
            parts.append(f"[{heading}]")

        return " ".join(parts)

    def _make_chunk(self, text, context_prefix, unit, doc_metadata):
        """Create a single chunk dict with metadata."""
        # Prepend context prefix to the text
        if context_prefix:
            full_text = f"{context_prefix}\n\n{text}"
        else:
            full_text = text

        # Build page number list
        page_start = unit.get("page_start", 1)
        page_end = unit.get("page_end", page_start)
        page_numbers = list(range(page_start, page_end + 1))

        return {
            "chunk_id": "",  # filled in later
            "text": full_text,
            "metadata": {
                "document_source": doc_metadata.get("document_source", ""),
                "document_category": doc_metadata.get("document_category", ""),
                "section_id": unit.get("section_id", ""),
                "section_heading": unit.get("heading", ""),
                "page_numbers": page_numbers,
                "chunk_index": 0,  # filled in later
                "total_chunks": 0,  # filled in later
                "structural_level": unit.get("level", 0),
            },
        }

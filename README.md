# RFP Sentinel — Multi-Agent RAG System for RFP-Based Bidder Shortlisting

An AI system that evaluates government RFP documents against authoritative government guidelines (GeM, BIS, DPIIT, MSME) to check compliance and flag deviations.

## Phase 1: Document Intelligence Pipeline

### Architecture

```
PDF Document
    ↓
[PDFLoader]          Extract raw text from each page
    ↓
[TextCleaner]        Strip Hindi/Devanagari, remove headers/footers,
                     normalize whitespace, clean PDF artifacts
    ↓
[HeaderExtractor]    Extract title, category, issuing authority
                     from document header using keyword matching
    ↓
[StructureParser]    Detect sections, clauses, sub-clauses using
                     regex patterns (SECTION/CHAPTER/numbered/etc.)
    ↓
[SmartChunker]       Structure-aware chunking:
                     - Never crosses section boundaries
                     - Small sections → 1 chunk
                     - Large sections → split at paragraph boundaries
                     - Every chunk gets section heading as context prefix
    ↓
JSON Output          Saved to data/processed_documents/
                     Each chunk has full metadata (section, page, category)
```

### Project Structure

```
RFP Sentinel Prototype/
├── app/
│   ├── ingestion/               # Document processing pipeline
│   │   ├── pdf_loader.py        # PDF → raw page text (PyMuPDF)
│   │   ├── text_cleaner.py      # Hindi stripping, whitespace normalization
│   │   ├── structure_parser.py  # Section/clause detection via regex
│   │   ├── smart_chunker.py     # Structure-aware chunking
│   │   ├── header_extractor.py  # Document title/category extraction
│   │   └── pipeline.py          # Orchestrates full ingestion flow
│   ├── embeddings/              # (Phase 1b) Nomic embeddings generation
│   ├── vectorstore/             # (Phase 1b) Qdrant vector storage
│   ├── rag/                     # (Phase 1b) RAG retrieval pipeline
│   ├── llm/                     # (Phase 1b) Llama 3.2 integration
│   ├── api/                     # (Phase 1b) FastAPI endpoints
│   └── dashboard/               # (Phase 1b) Evaluation UI
├── data/
│   ├── raw_documents/           # Source PDFs organized by category
│   │   ├── gem/                 # GeM GTC, Bid Docs, ITBs, ATCs
│   │   ├── bis/                 # BIS standards and testing handbooks
│   │   ├── dpiit/               # DPIIT policies
│   │   └── enterprise/          # MSME, Startup policies
│   ├── processed_documents/     # JSON output from ingestion pipeline
│   └── uploaded_rfps/           # User-uploaded RFPs for evaluation
├── requirements.txt
└── README.md
```

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Process all documents
python app/ingestion/pipeline.py

# Process a single document
python app/ingestion/pipeline.py data/raw_documents/gem/GeM-GTC-40-1740735825.pdf
```

### How It Works

#### Why Not Fixed-Size Chunking?

Government documents have structured hierarchy (Section → Clause → Sub-clause). Fixed-size chunking with overlap can merge text from two different sections into one chunk. When two consecutive sections discuss different topics (e.g., EMD requirements vs. warranty terms), this causes the LLM to hallucinate by mixing contexts.

**Our approach**: Detect structure first, then chunk within boundaries.

#### Structure Detection

The parser detects these patterns (in priority order):

| Pattern | Example | Level |
|---|---|---|
| SECTION/CHAPTER/PART | `SECTION III - ELIGIBILITY` | 1 (Major) |
| ANNEXURE/APPENDIX | `ANNEXURE A` | 1 (Major) |
| Numbered sections `N.` | `2. General Terms` | 2 (Section) |
| Sub-sections `N.N` | `2.5 Earnest Money Deposit` | 3 (Sub-section) |
| ALL-CAPS headings | `ADDITIONAL TERMS AND CONDITIONS` | 2 (Section) |
| Roman numerals `i.`, `ii.` | `viii. The seller would...` | 3 (Item) |
| Alpha items `a.`, `b.` | `a. "APPLICABLE LAWS"...` | 4 (Item) |
| Parenthetical `(1)`, `(a)` | `(2) It shall come into force...` | 4 (Item) |

#### Chunk Context Prefix

Every chunk gets its parent section heading prepended:

```
[Section 2.5: Earnest Money Deposit (EMD)]

Bidders must submit an EMD of Rs. 5,00,000 via Bank Guarantee...
```

This ensures the LLM always knows which section/clause it's reading, even when the chunk is retrieved in isolation.

### Adding New Documents

1. Place the PDF in the appropriate folder under `data/raw_documents/`
2. If it's a new category, create a new folder (e.g., `data/raw_documents/dpiit/`)
3. Run the pipeline: `python app/ingestion/pipeline.py`
4. Check the JSON output in `data/processed_documents/`

The system auto-detects the document category from the document header. To add new category rules, edit `CATEGORY_RULES` in `app/ingestion/header_extractor.py`.

---

## Future Upgrades (Phase 2+)

These enhancements are planned but not yet implemented:

### Metadata Enhancements
- **LLM-based metadata extraction** — Use the LLM to classify documents and extract richer metadata (effective dates, superseded documents, applicability scope)
- **Document versioning** — Track when a document is updated and re-ingest only changed sections
- **Cross-reference linking** — Detect when one document references another (e.g., "as per GeM GTC Clause 5.2")

### Content Processing
- **Table extraction** — Detect and preserve table structures (currently tables become flat text)
- **OCR support** — Handle scanned PDFs using Tesseract
- **Image/diagram extraction** — Extract flowcharts and diagrams from documents

### Quality & Confidence
- **Confidence scoring** — Attach a confidence score to each chunk's structure detection
- **Chunk quality validation** — Automated checks for incomplete sentences, broken references
- **Embedding quality analysis** — Measure semantic coherence of chunks

### Scalability
- **Incremental ingestion** — Only process new/changed documents
- **Parallel processing** — Process multiple documents simultaneously
- **Database-backed metadata** — Move from JSON files to a proper metadata store

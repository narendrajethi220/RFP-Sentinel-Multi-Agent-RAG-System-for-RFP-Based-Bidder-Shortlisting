from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.text_cleaner import TextCleaner
from app.ingestion.semantic_chunker import SemanticChunker

loader = PDFLoader(
    "./data/raw_documents/gem/GeM-GTC-40-1740735825.pdf"
)

pages = loader.load()

cleaner = TextCleaner()

clean_pages = []

for page in pages:
    clean_pages.append(
        {
            "page_number":page["page_number"],
            "text":page["text"]
        }
    )

chunker = SemanticChunker()

chunks = chunker.chunk(
    clean_pages
)

print("Total chunks: ",len(chunks))

print("\n CHUNKS\n")

print(chunks[3]["text"])
from app.ingestion.pdf_loader import PDFLoader

pdf = PDFLoader(
    "./data/raw_documents/gem/GeM-GTC-40-1740735825.pdf"
)

pages = pdf.load()

print("Total Pages: ",len(pages))

print(pages[0]["text"][:500])
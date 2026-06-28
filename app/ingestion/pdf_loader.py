import pymupdf # 

class PDFLoader:
    def __init__(self,file_path):
        self.file_path = file_path
    
    def load(self):
        
        document = pymupdf.open(self.file_path)

        pages = []

        for page_number, page in enumerate(document):

            text = page.get_text()

            pages.append(
                {
                "page_number":page_number + 1,
                "text": text
                }
            )
    
        return pages
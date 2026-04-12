import os
from pathlib import Path
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024,
            chunk_overlap=200,
            length_function=len,
        )

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
        return text

    def process_and_chunk_pdf(self, pdf_path, category="General"):
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return []
            
        chunks = self.text_splitter.create_documents(
            [text],
            metadatas=[{"source": str(pdf_path), "category": category}]
        )
        return chunks
        
if __name__ == "__main__":
    processor = DocumentProcessor()
    print("DocumentProcessor initialized.")

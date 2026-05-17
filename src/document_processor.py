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
    import json
    from config import RAW_DATA_DIR, PROCESSED_DATA_DIR
    processor = DocumentProcessor()
    print("Starting document processing...")
    
    all_chunks_data = []
    
    if os.path.exists(RAW_DATA_DIR):
        for filename in os.listdir(RAW_DATA_DIR):
            if filename.endswith(".pdf"):
                file_path = os.path.join(RAW_DATA_DIR, filename)
                print(f"Processing {filename}...")
                chunks = processor.process_and_chunk_pdf(file_path, category="General")
                
                # Convert LangChain chunks to dicts
                for chunk in chunks:
                    all_chunks_data.append({
                        "content": chunk.page_content,
                        "metadata": chunk.metadata
                    })
                    
    output_path = os.path.join(PROCESSED_DATA_DIR, "processed_chunks.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks_data, f, indent=4)
        print(f"Total {len(all_chunks_data)} chunks saved to {output_path}")

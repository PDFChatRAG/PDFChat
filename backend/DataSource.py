from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
from docx import Document
import os

def processFile(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == ".pdf":
        return extractTextFromPdf(file_path)
    elif file_extension == ".docx":
        return extractTextFromDocx(file_path)
    elif file_extension == ".txt":
        return extractTextFromTxt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

def extractTextFromPdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extractTextFromDocx(file_path):
    doc = Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extractTextFromTxt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    return text

def splitTextIntoChunks(text, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )
    chunks = text_splitter.split_text(text)
    return chunks
    
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from docx import Document
from io import BytesIO
import os

def processFile(file_path, file_obj=None):

    if file_obj is None:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)
        file_obj = file_path
    
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == ".pdf":
        return extractTextFromPdf(file_obj)
    elif file_extension == ".docx":
        return extractTextFromDocx(file_obj)
    elif file_extension == ".txt":
        return extractTextFromTxt(file_obj)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

def extractTextFromPdf(file_obj):

    reader = PdfReader(file_obj)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extractTextFromDocx(file_obj):

    doc = Document(file_obj)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extractTextFromTxt(file_obj):

    if isinstance(file_obj, (str, os.PathLike)):
        with open(file_obj, 'r', encoding='utf-8') as file:
            text = file.read()
    elif isinstance(file_obj, BytesIO):
        text = file_obj.getvalue().decode('utf-8')
    else:
        # Handle file-like objects
        text = file_obj.read()
        if isinstance(text, bytes):
            text = text.decode('utf-8')
    return text

def splitTextIntoChunks(text, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )
    chunks = text_splitter.split_text(text)
    return chunks
    
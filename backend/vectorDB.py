import os
from langchain_chroma import Chroma
from langchain.tools import tool
from langchain_core.documents import Document 

import DataSource


#In a vector database like Chroma, you can think of the 
# collection_name as a table name in a traditional database or a folder name on your computer.
def create_vector_store(embedding, collection_name):
    return Chroma(
        collection_name=collection_name,
        embedding_function=embedding,
        persist_directory="./chroma_db"
    )

def add_documents_to_vector_store(vector_store):
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(backend_dir, '..', 'resources', 'bill.pdf')
    text = DataSource.processFile(pdf_path)
    chunks = DataSource.splitTextIntoChunks(text)
    docs = [Document(page_content=chunk) for chunk in chunks]
    ids = [f"chunk-{i}" for i in range(len(docs))]
    vector_store.add_documents(documents=docs, ids=ids)

def initialize_vector_store(embedding, collection_name):
    vector_store = create_vector_store(embedding, collection_name)
    add_documents_to_vector_store(vector_store)
    return vector_store




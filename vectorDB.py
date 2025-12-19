import os
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.tools import tool


#In a vector database like Chroma, you can think of the 
# collection_name as a table name in a traditional database or a folder name on your computer.
def create_vector_store(embedding, collection_name):
    return Chroma(
        collection_name=collection_name,
        embedding_function=embedding,
        persist_directory="./chroma_db"
    )

@tool
def add_documents_to_vector_store(vector_store, docs, ids):
    vector_store.add_documents(documents=docs, ids=ids)

@tool
def search_similar_documents(vector_store, query, k):
    return vector_store.similarity_search(query, k=k)




import os
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings



def create_vector_store(embedding):
    return InMemoryVectorStore(embedding)

def add_documents_to_vector_store(vector_store, docs, ids):
    vector_store.add_documents(docs, ids=ids)

def search_similar_documents(vector_store, query, k):
    return vector_store.similarity_search(query, k=k)




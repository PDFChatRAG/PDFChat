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

def add_documents_to_vector_store(vector_store, docs, ids):
    vector_store.add_documents(documents=docs, ids=ids)

def create_retriever_tool(vector_store):
    @tool(response_format="content_and_artifact")
    def search_similar_documents(query: str):
        """Search the uploaded PDF for information to answer the user's query."""
        retrieved_docs = vector_store.similarity_search(query, k=2)
        serialized = "\n\n".join(
            (f"Content: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs
    
    return search_similar_documents




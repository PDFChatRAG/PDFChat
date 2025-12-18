from langchain_google_genai import GoogleGenerativeAIEmbeddings

def embed(chunkList):
    embeddingModel = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-004")
    embeddings = embeddingModel.embed_documents(chunkList)
    return embeddings

import os
import dotenv
import getpass
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document 
from langchain_chroma import Chroma

from vectorDB import create_vector_store, add_documents_to_vector_store, search_similar_documents
from DataSource import processFile, splitTextIntoChunks


dotenv.load_dotenv()
def main():
    # if not os.environ.get("GOOGLE_API_KEY"):
    #     os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter Google API key: ")

    vector_store = create_vector_store(GoogleGenerativeAIEmbeddings(model="models/text-embedding-004"), "documents_collection")
    text = processFile("bill.pdf")
    print("Extracted text from file:")
    print(text)
    
    chunks = splitTextIntoChunks(text)
    docs = [Document(page_content=chunk) for chunk in chunks]
    print("Created Document objects from chunks.")
    print(docs)
    print(f"Split text into {len(chunks)} chunks.")
    ids = [f"chunk-{i}" for i in range(len(docs))]
    add_documents_to_vector_store(vector_store, docs, ids)

    # model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
    # system_msg= "You are a helpful assistant. You will be provided with a user's question and a set of retrieved documents from a knowledge base. Instructions: 1. Use only the provided context to answer the question. 2. If the answer is not contained within the context, clearly state that you do not have enough information to answer. 3. Do not use any prior knowledge or external information. 4. Keep your answer concise and factual."
    # prompt = [(
    #     "system",
    #     system_msg,
    #     )]
    # print("Input prompt to the model:")
    # humanMessage = input()
    # prompt.append(("human", humanMessage))
    # response = model.invoke(prompt)
    print("Searching for similar documents to the query...")
    print("found answer:")
    results = search_similar_documents(vector_store, "What is the late fee?", k=1)
    if results:
        doc = results[0]
        print("\n" + "="*30)
        print("Top Relevant Match Found:")
        print("="*30)
        print(doc.page_content)
        print("="*30 + "\n")
    else:
        print("No matches found.")
    


if __name__ == "__main__":
    main()
import os
import dotenv
import getpass
from langchain_google_genai import ChatGoogleGenerativeAI


dotenv.load_dotenv()
def main():
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter Google API key: ")

    model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
    prompt = [(
        "system",
        "You are a helpful assistant that helps a new developer learn to use the Google Generative AI API to create a RAG chatbot.",
        )]
    print("Input prompt to the model:")
    humanMessage = input()
    prompt.append(("human", humanMessage))
    response = model.invoke(prompt)
    print(response.text)
    


if __name__ == "__main__":
    main()
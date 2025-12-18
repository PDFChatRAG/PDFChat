import os
import dotenv
import getpass
import chatBot

dotenv.load_dotenv()
def main():
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter Google API key: ")

    print("Please Enter User ID: ")
    userId = input().strip()
    chatWithMemory, sessionId = chatBot.initialize_chatbot(userId)

    while True:
        print(chatBot.chatBot(chatWithMemory, sessionId))
    


if __name__ == "__main__":
    main()
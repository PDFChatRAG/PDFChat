import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import sys
import os
import dotenv
import getpass

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import chatBot

class PDFChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDFChat")
        self.root.geometry("800x600")
        
        # Initialize environment
        dotenv.load_dotenv()
        if not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter Google API key: ")
        
        self.chatWithMemory = None
        self.sessionId = None
        
        # Header
        header = ttk.Label(root, text="PDFChat - Chat with Your PDFs", font=("Arial", 16, "bold"))
        header.pack(pady=10)
        
        # Chat display area
        self.chat_display = tk.Text(root, height=20, width=80, state="disabled")
        self.chat_display.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Input frame
        input_frame = ttk.Frame(root)
        input_frame.pack(pady=10, padx=10, fill="x")
        
        self.input_field = ttk.Entry(input_frame)
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_field.bind("<Return>", lambda e: self.send_message_thread())
        
        ttk.Button(input_frame, text="Send", command=self.send_message_thread).pack(side="left")
        
        # Initialize chatbot with user ID
        self.initialize_session()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        chatBot._memory_manager.__exit__(None, None, None)
        self.root.destroy()

    def initialize_session(self):
        """Initialize chatbot session with user ID"""
        # Create a simple dialog to get user ID
        user_id = tk.simpledialog.askstring("User ID", "Enter your User ID:")
        
        if user_id is None or user_id.strip() == "":
            user_id = "default_user"
        
        self.sessionId = user_id
        self.chatWithMemory, self.sessionId = chatBot.initialize_chatbot(user_id)
        self.display_message(f"System: Chatbot initialized for user '{user_id}'.")
    
    def send_message_thread(self):
        """Send message in a separate thread to prevent GUI freezing"""
        threading.Thread(target=self.send_message, daemon=True).start()
    
    def send_message(self):
        message = self.input_field.get()
        if message.strip():
            self.display_message(f"You: {message}")
            self.input_field.delete(0, tk.END)
            
            try:
                # Use the same chatBot function as app.py
                response = chatBot.chatBot(self.chatWithMemory, self.sessionId, message)
                self.display_message(f"Bot: {response}")
                
            except Exception as e:
                self.display_message(f"System: Error - {str(e)}")
    
    def display_message(self, message):
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFChatGUI(root)
    root.mainloop()
# PDFChat 📄💬


A Retrieval-Augmented Generation (RAG) chatbot powered by Google's Generative AI API and LangChain. This project demonstrates how to build an intelligent assistant that can get information from PDFs and answer any questions from the user about the PDFs.

## 🖥️ REST API Backend

PDFChat now includes a FastAPI backend for easy integration with web frontends (such as ReactJS).

### Running the API Locally

1. **Install dependencies**
   ```bash
   pip install fastapi uvicorn
   ```
2. **Start the API server**
   ```bash
   uvicorn backend.api:app --reload
   ```
   The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000)
3. **Interactive API docs**
   - Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger UI.

### API Endpoints

- `POST /session` — Start a new chat session. Request: `{ "user_id": "..." }` Response: `{ "session_id": "..." }`
- `POST /chat` — Send a message. Request: `{ "session_id": "...", "message": "..." }` Response: `{ "response": "..." }`
- `POST /upload` — Upload a PDF, DOCX, or TXT file for processing. (Max 100MB)

You can use these endpoints from your frontend or API client.

## 🎯 Overview

PDFChat is a conversational AI system that leverages:
- **Google Generative AI**: Using the Gemini 3 Flash model for fast, intelligent responses
- **LangChain**: A framework for building applications with language models
- **Vector Database**: For semantic search and document retrieval
- **Embeddings**: To understand and match user queries with relevant content

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Google API Key (get one at [Google AI Studio](https://ai.google.dev/))
- pip or conda package manager

### Installation

1. **Clone or download this project**
   ```bash
   cd PDFChat
   ```

2. **Create and configure environment variables**
   ```bash
   cp .env-template .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   Or with conda:
   ```bash
   conda create --name pdfchat --file requirements.txt
   conda activate pdfchat
   ```

## 📦 Project Structure

- **backend/api.py** - FastAPI REST API backend
- **backend/embed.py** - Handles document embedding functionality
- **backend/vectorDB.py** - Vector database management for semantic search
- **backend/DataSource.py** - Manages PDF and document data sources
- **backend/utils.py** - Utility functions and helper methods
- **backend/dto/** - Data transfer objects for API requests/responses
- **requirements.txt** - Project dependencies

## ⚙️ Configuration

### Environment Variables
Set up the following in your `.env` file:

```
GOOGLE_API_KEY=your_api_key_here
```

If not provided at startup, you'll be prompted to enter your Google API key.

## 🔧 Key Dependencies

- **langchain-google-genai** - LangChain integration with Google's Generative AI
- **langchain-core** - Core LangChain framework
- **google-genai** - Google's Generative AI client library
- **dotenv** - Environment variable management
- **google-auth** - Authentication for Google APIs


## 💡 Usage

You can interact with the API using tools like curl, Postman, or from your frontend app.

### Authentication Flow

1. **Register a new user**
   ```bash
   curl -X POST "http://127.0.0.1:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password123"}'
   ```

2. **Login to get session token**
   ```bash
   curl -X POST "http://127.0.0.1:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password123"}'
   # Response: {"access_token": "...", "token_type": "bearer", "session_id": "..."}
   ```

3. **Create a session**
   ```bash
   curl -X POST "http://127.0.0.1:8000/sessions" \
     -H "Authorization: Bearer {access_token}"
   # Response: {"session_id": "..."}
   ```

4. **Send a chat message** (session-isolated)
   ```bash
   curl -X POST "http://127.0.0.1:8000/chat" \
     -H "Authorization: Bearer {access_token}" \
     -H "Content-Type: application/json" \
     -d '{"message": "What does this document say?"}'
   ```

5. **Upload a file to current session**
   ```bash
   curl -X POST "http://127.0.0.1:8000/sessions/{session_id}/upload" \
     -H "Authorization: Bearer {access_token}" \
     -F "file=@/path/to/document.pdf"
   ```

6. **List your sessions**
   ```bash
   curl -X GET "http://127.0.0.1:8000/sessions" \
     -H "Authorization: Bearer {access_token}"
   ```

## 🏗️ Architecture (v2.0)

### Multi-User, Multi-Session Design

PDFChat now supports a sophisticated session management system similar to ChatGPT and Gemini:

#### Key Features:
- **User Authentication**: Secure stateful session management
- **Multiple Sessions Per User**: Each user can create unlimited sessions
- **Session Isolation**: Each session has:
  - Isolated chat memory (conversation history)
  - Isolated vector database collection (documents)
  - Separate conversation context
- **Auto-Archival**: Sessions are automatically archived after 30 days of inactivity
- **Session Lifecycle**: Active → Archived → Deleted (with recovery options)
- **Document Tracking**: File uploads are tracked per session with metadata

#### Database Schema:
- **Users**: User accounts with email and hashed passwords
- **Sessions**: User sessions with status (active/archived/deleted)
- **Documents**: Files uploaded to sessions with chunk counts and metadata
- **AuthSession**: Stateful session tokens for user authentication

#### Vector Database:
- Session-isolated Chroma collections named: `user_{user_id}_session_{session_id}`
- Document metadata includes source file name, chunk index, and upload timestamp
- Immediate cleanup of documents when session is hard-deleted

### System Components:

| Module | Purpose |
|--------|---------|
| `models.py` | SQLAlchemy ORM models (User, Session, Document, TokenBlacklist) |
| `database.py` | Database connection and session management |
| `auth_service.py` | Session token generation, password hashing, validation |
| `session_lifecycle.py` | Session state machine and auto-archival policies |
| `sessionManager.py` | Session CRUD operations with ownership verification |
| `vectorDB.py` | Session-isolated vector store management |
| `chatBot.py` | Factory pattern for creating session-specific ChatBot instances |
| `api.py` | FastAPI REST API with authentication and multi-session support |

## 🔐 Authentication

The application uses **Stateful Database Sessions** for authentication.

- **Login**: The server generates a random session token and stores it in the database.
- **Session Validation**: On every request, the server checks the database to ensure the token is valid and active.
- **Logout**: The session is deleted from the database, instantly revoking access.

### Session Structure
The `AuthSession` model tracks:
- `token`: Unique random string (Session ID)
- `user_id`: The user who owns the session
- `chat_session_id`: The active chat context (optional)
- `expires_at`: When the session expires (default 24 hours)

## 🛠️ Development

### Adding Features
- **Modify embeddings**: Update `vectorDB.py` to change embedding strategies
- **Extend vector DB**: Enhance VectorDBService for custom database operations
- **Add data sources**: Update `dataSource.py` to support additional document formats
- **Session policies**: Adjust `SESSION_INACTIVITY_DAYS` and `SESSION_RETENTION_DAYS` in `.env`

### Testing
Start the development server:
```bash
uvicorn api:app --reload
```

Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive API documentation (Swagger UI).

## 📋 Future Enhancements

- [ ] APScheduler integration for automatic session cleanup
- [ ] Session sharing and collaboration features
- [ ] Advanced document indexing and full-text search
- [ ] Session export/import functionality
- [ ] Conversation analytics and insights
- [ ] Rate limiting and usage quotas per user
- [ ] Multi-modal document support (images, audio)

## 📝 License

This project is provided as-is for educational purposes.
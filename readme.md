# PDFChat 📄💬

A Retrieval-Augmented Generation (RAG) chatbot powered by Google's Generative AI API and LangChain. This project demonstrates how to build an intelligent assistant that can get information from PDFs and answer any questions from the user about the PDFs.

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

4. **Run the application**
   ```bash
   python app.py
   ```

## 📦 Project Structure

- **app.py** - Main entry point for the chatbot application
- **embed.py** - Handles document embedding functionality
- **vectorDB.py** - Vector database management for semantic search
- **DataSource.py** - Manages PDF and document data sources
- **utils.py** - Utility functions and helper methods
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

Run the application and interact with the chatbot:

```bash
python app.py
Input prompt to the model:
> Your question here
```

The model will respond with information from the PDF user uploaded.

## 🛠️ Development

### Adding Features
- **Modify embeddings**: Update `embed.py` to change embedding strategies
- **Extend vector DB**: Enhance `vectorDB.py` for custom database operations
- **Add data sources**: Update `DataSource.py` to support additional document formats
- **Utilities**: Add helper functions to `utils.py`

### Testing
Run individual modules to test functionality during development.

## 📝 License

This project is provided as-is for educational purposes.
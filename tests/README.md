# PDFChat Unit and Integration Tests

## Overview

This directory contains comprehensive unit and integration tests for the PDFChat project, a multi-user, multi-session RAG chatbot application. The tests are organized into unit tests (isolated component testing) and integration tests (API endpoint testing).

## Directory Structure

```
tests/
├── conftest.py              # Shared pytest fixtures and configuration
├── pytest.ini               # Pytest configuration
├── fixtures/
│   ├── factories.py         # Test data factories (UserFactory, SessionFactory, etc.)
│   └── __init__.py
├── mocks/
│   ├── __init__.py          # Mock implementations for external dependencies
│   └── (MockLLM, MockChromaVector, etc.)
├── unit/
│   ├── test_auth_service.py       # AuthService tests (password hashing, JWT)
│   ├── test_models.py              # SQLAlchemy model tests
│   ├── test_session_manager.py     # SessionManager CRUD tests
│   ├── test_session_lifecycle.py   # Session state transitions and archival
│   ├── test_data_source.py         # Document processing and text extraction
│   ├── test_vector_db.py           # Vector database operations
│   └── __init__.py
└── integration/
    ├── test_api_endpoints.py       # FastAPI endpoint tests
    └── __init__.py
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/unit/test_auth_service.py
```

### Run specific test class
```bash
pytest tests/unit/test_auth_service.py::TestAuthServicePasswordHashing
```

### Run specific test
```bash
pytest tests/unit/test_auth_service.py::TestAuthServicePasswordHashing::test_hash_password
```

### Run tests by marker
```bash
pytest -m unit              # Run only unit tests
pytest -m integration       # Run only integration tests
pytest -m auth              # Run authentication tests
pytest -m database          # Run database tests
```

### Run with coverage report
```bash
pytest --cov=. --cov-report=html
```

### Run tests in parallel (requires pytest-xdist)
```bash
pytest -n auto
```

### Run with verbose output
```bash
pytest -v
```

### Run with specific log level
```bash
pytest --log-cli-level=DEBUG
```

## Test Organization

### Unit Tests

#### `test_auth_service.py`
- **Password Hashing**: Tests for password hashing and verification
- **JWT Creation**: Tests for access and refresh token creation
- **Token Validation**: Tests for token verification and claims extraction
- **Edge Cases**: Tests for edge cases like empty passwords, special characters

#### `test_models.py`
- **User Model**: Tests for user creation, uniqueness, relationships
- **Session Model**: Tests for session creation, status, metadata
- **Document Model**: Tests for document tracking and relationships
- **TokenBlacklist Model**: Tests for token revocation
- **Database Relationships**: Tests for cascade deletes and complex queries

#### `test_session_manager.py`
- **CRUD Operations**: Tests for create, read, update, delete operations
- **Session Listing**: Tests for filtering by status, user isolation
- **Document Management**: Tests for adding and retrieving documents
- **Activity Tracking**: Tests for timestamp updates
- **Session Deletion**: Tests for soft delete (archive) and hard delete

#### `test_session_lifecycle.py`
- **State Transitions**: Tests for valid and invalid state transitions
- **Soft Delete/Archive**: Tests for archiving sessions
- **Restore**: Tests for restoring archived sessions
- **Permanent Delete**: Tests for hard deletion and cleanup
- **Archival Policy**: Tests for auto-archival based on inactivity and retention

#### `test_data_source.py`
- **File Processing**: Tests for PDF, DOCX, and TXT processing
- **Text Extraction**: Tests for extracting text from various formats
- **Text Chunking**: Tests for splitting text into chunks with overlap
- **Edge Cases**: Tests for special characters, large files, empty files

#### `test_vector_db.py`
- **Collection Management**: Tests for creating and loading vector collections
- **Document Embedding**: Tests for processing documents into vectors
- **Session Isolation**: Tests for collection name uniqueness per session
- **Retriever**: Tests for creating document retrievers
- **Cleanup**: Tests for deleting collections and cleanup operations

### Integration Tests

#### `test_api_endpoints.py`
- **Authentication**: Tests for register, login, refresh, logout endpoints
- **Session Management**: Tests for session CRUD and state transitions
- **Chat**: Tests for sending messages to the chatbot
- **Conversation History**: Tests for retrieving message history
- **File Upload**: Tests for uploading and processing documents
- **Error Handling**: Tests for invalid requests and error responses
- **Security**: Tests for authorization, token validation, permission checks

## Fixtures

The `conftest.py` provides shared fixtures:

### Database Fixtures
- `test_db`: In-memory SQLite database
- `db_session`: Database session for each test
- `app_with_db`: FastAPI app with test database

### Authentication Fixtures
- `auth_service`: AuthService instance
- `test_user`: Pre-created test user
- `valid_jwt_token`: Valid JWT token
- `expired_jwt_token`: Expired JWT token

### Data Fixtures
- `test_session_data`: Pre-created test session
- `test_pdf_content`: Sample PDF content
- `test_docx_content`: Sample DOCX content
- `test_txt_content`: Sample text content

### Mock Fixtures
- `mock_google_genai`: Mocked Google Generative AI LLM
- `mock_embeddings`: Mocked embeddings
- `mock_chroma`: Mocked Chroma vector store
- `mock_checkpointer`: Mocked LangGraph checkpointer
- `mock_pdf_loader`: Mocked PDF loader
- `mock_docx_loader`: Mocked DOCX loader

### HTTP Fixtures
- `client`: TestClient for FastAPI

## Test Data Factories

The `tests/fixtures/factories.py` provides factory classes for creating test data:

### UserFactory
```python
user, password = UserFactory.create(db_session, email="test@example.com")
users = UserFactory.create_batch(db_session, count=5)
```

### SessionFactory
```python
session = SessionFactory.create(db_session, user_id=user.id, title="Test Session")
sessions = SessionFactory.create_batch(db_session, user_id=user.id, count=5)
```

### DocumentFactory
```python
document = DocumentFactory.create(db_session, session_id=session.id, file_type="pdf")
documents = DocumentFactory.create_batch(db_session, session_id=session.id, count=3)
```

### TokenBlacklistFactory
```python
token = TokenBlacklistFactory.create(db_session, user_id=user.id)
```

## Mocks

The `tests/mocks/` module provides mock implementations:

- **MockLLM**: Mocked Google Generative AI LLM with predictable responses
- **MockEmbeddings**: Mocked embedding generation
- **MockChromaVector**: Mocked Chroma vector store
- **MockCheckpointer**: Mocked LangGraph state checkpointer
- **MockRetriever**: Mocked document retriever
- **MockMessage**: Mocked LangChain message objects

## Configuration

### pytest.ini
- Test discovery patterns
- Coverage configuration with HTML reports
- Test markers for categorization
- Async test mode configuration
- Log file configuration
- Test timeout settings

### Markers
Use markers to categorize and run specific test subsets:

```python
@pytest.mark.unit
@pytest.mark.auth
def test_something():
    pass
```

## Coverage

Tests are configured to report code coverage using pytest-cov:

```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

Coverage reports are generated in:
- **HTML Report**: `htmlcov/index.html`
- **Terminal Report**: Console output with missing lines
- **XML Report**: `coverage.xml` (for CI/CD integration)

## Continuous Integration

The test suite is designed to work with CI/CD pipelines:

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests with coverage
pytest --cov=. --cov-report=xml

# Generate test report (if using pytest-json-report)
pytest --json-report --json-report-file=report.json
```

## Best Practices

1. **Isolation**: Each test should be independent and not rely on state from other tests
2. **Mocking**: Mock external dependencies (LLM, vector DB) to ensure deterministic tests
3. **Fixtures**: Use fixtures for common setup (database, authentication, etc.)
4. **Factories**: Use factories to create test data consistently
5. **Naming**: Test names should clearly describe what is being tested
6. **Coverage**: Aim for high code coverage but focus on critical paths
7. **Performance**: Keep tests fast - use in-memory databases and mocks
8. **Async Tests**: Use `pytest-asyncio` for testing async functions

## Troubleshooting

### Tests fail with "database is locked"
- Ensure tests are using in-memory SQLite (`:memory:`)
- Check that each test has its own database session
- Use `StaticPool` to prevent connection pooling issues

### Mocked LLM not being used
- Check that patches are applied at the correct import path
- Ensure mocks are set up before creating objects that use them
- Use `@patch` decorator on test methods or fixtures

### Token validation failures
- Verify token expiration time is set correctly
- Check that JWT secret key is consistent
- Ensure token type (access vs refresh) is correct

### File upload tests fail
- Use in-memory BytesIO instead of actual files
- Mock file processing functions
- Verify multipart/form-data encoding is correct

## Contributing

When adding new tests:

1. Follow the existing directory structure
2. Use factory classes to create test data
3. Mock external dependencies
4. Add appropriate markers
5. Document non-obvious test logic
6. Ensure tests are deterministic (no time-dependent logic)
7. Update this README if adding new test categories

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#session-faq-defaults)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

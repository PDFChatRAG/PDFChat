"""
Additional tests for dataSource.py coverage.
"""
import pytest
import os
from io import BytesIO
from dataSource import processFile, extractTextFromTxt

def test_process_file_not_found():
    """Test processFile with non-existent file."""
    with pytest.raises(FileNotFoundError):
        processFile("non_existent_file.pdf")

def test_extract_text_from_txt_bytes_io():
    """Test extracting text from BytesIO object."""
    content = "Hello World"
    file_obj = BytesIO(content.encode('utf-8'))
    text = extractTextFromTxt(file_obj)
    assert text == content

def test_extract_text_from_txt_bytes():
    """Test extracting text from raw bytes (file-like read returns bytes)."""
    # Mock a file-like object that returns bytes on read
    class BytesFile:
        def read(self):
            return b"Hello Bytes"
            
    text = extractTextFromTxt(BytesFile())
    assert text == "Hello Bytes"

def test_process_file_with_file_obj():
    """Test processFile with provided file_obj."""
    # Test with a mock PDF or just trigger the logic
    # We can use a txt file for simplicity
    content = "Direct object content"
    file_obj = BytesIO(content.encode('utf-8'))
    
    # We need to pass file_path to determine extension
    text = processFile("dummy.txt", file_obj)
    assert text == content

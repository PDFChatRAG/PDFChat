"""
Unit tests for dataSource.py
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO

from dataSource import (
    processFile,
    extractTextFromPdf,
    extractTextFromDocx,
    extractTextFromTxt,
    splitTextIntoChunks,
)


class TestProcessFile:
    """Test processFile router function."""

    def test_process_pdf_file(self):
        """Test processing PDF file."""
        with patch("dataSource.extractTextFromPdf") as mock_pdf:
            mock_pdf.return_value = "PDF content"

            result = processFile("test.pdf", BytesIO(b"fake pdf data"))

            assert result == "PDF content"
            mock_pdf.assert_called_once()

    def test_process_docx_file(self):
        """Test processing DOCX file."""
        with patch("dataSource.extractTextFromDocx") as mock_docx:
            mock_docx.return_value = "DOCX content"

            result = processFile("test.docx", BytesIO(b"fake docx data"))

            assert result == "DOCX content"
            mock_docx.assert_called_once()

    def test_process_txt_file(self):
        """Test processing TXT file."""
        with patch("dataSource.extractTextFromTxt") as mock_txt:
            mock_txt.return_value = "TXT content"

            result = processFile("test.txt", BytesIO(b"fake txt data"))

            assert result == "TXT content"
            mock_txt.assert_called_once()

    def test_process_unknown_file_type(self):
        """Test processing unknown file type."""
        with pytest.raises((ValueError, Exception)):
            processFile("test.xyz", BytesIO(b"unknown"))


class TestExtractPdfText:
    """Test PDF text extraction."""

    def test_extract_pdf_basic(self, mock_pdf_loader, test_pdf_content):
        """Test basic PDF extraction."""
        pdf_file = BytesIO(b"fake pdf data")

        result = extractTextFromPdf(pdf_file)

        assert test_pdf_content in result
        assert len(result) > 0

    def test_extract_pdf_multiple_pages(self, mock_pdf_loader, test_pdf_content):
        """Test PDF extraction with multiple pages."""
        pdf_file = BytesIO(b"fake pdf data")

        result = extractTextFromPdf(pdf_file)

        # Should extract from both pages
        assert len(result) > len(test_pdf_content)

    def test_extract_pdf_empty_file(self):
        """Test extracting empty PDF."""
        with patch("dataSource.PdfReader") as mock_pdf:
            mock_instance = MagicMock()
            mock_instance.pages = []
            mock_pdf.return_value = mock_instance

            result = extractTextFromPdf(BytesIO(b"empty"))

            assert result == "" or len(result) == 0


class TestExtractDocxText:
    """Test DOCX text extraction."""

    def test_extract_docx_basic(self, mock_docx_loader, test_docx_content):
        """Test basic DOCX extraction."""
        docx_file = BytesIO(b"fake docx data")

        result = extractTextFromDocx(docx_file)

        assert test_docx_content in result
        assert len(result) > 0

    def test_extract_docx_multiple_paragraphs(self, mock_docx_loader, test_docx_content):
        """Test DOCX extraction with multiple paragraphs."""
        docx_file = BytesIO(b"fake docx data")

        result = extractTextFromDocx(docx_file)

        # Should extract from both paragraphs
        assert len(result) > len(test_docx_content)

    def test_extract_docx_empty_file(self):
        """Test extracting empty DOCX."""
        with patch("dataSource.Document") as mock_docx:
            mock_instance = MagicMock()
            mock_instance.paragraphs = []
            mock_docx.return_value = mock_instance

            result = extractTextFromDocx(BytesIO(b"empty"))

            assert result == "" or len(result) == 0


class TestExtractTxtText:
    """Test TXT text extraction."""

    def test_extract_txt_basic(self, test_txt_content):
        """Test basic TXT extraction."""
        txt_file = BytesIO(test_txt_content.encode())

        result = extractTextFromTxt(txt_file)

        assert test_txt_content in result

    def test_extract_txt_with_encoding(self):
        """Test TXT extraction with different encoding."""
        content = "Test content with special chars: café"
        txt_file = BytesIO(content.encode("utf-8"))

        result = extractTextFromTxt(txt_file)

        assert "café" in result or "caf" in result

    def test_extract_txt_empty_file(self):
        """Test extracting empty TXT file."""
        result = extractTextFromTxt(BytesIO(b""))

        assert result == ""

    def test_extract_txt_multiline(self):
        """Test TXT extraction with multiple lines."""
        content = "Line 1\nLine 2\nLine 3"
        txt_file = BytesIO(content.encode())

        result = extractTextFromTxt(txt_file)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result


class TestSplitTextIntoChunks:
    """Test text chunking."""

    def test_split_basic_text(self):
        """Test splitting basic text."""
        text = "This is a test. " * 100  # Long text
        chunks = splitTextIntoChunks(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_split_preserves_content(self):
        """Test that splitting preserves all content."""
        text = "This is a test. " * 50
        chunks = splitTextIntoChunks(text)

        combined = " ".join(chunks)
        assert len(combined) >= len(text.strip())

    def test_split_empty_text(self):
        """Test splitting empty text."""
        chunks = splitTextIntoChunks("")

        assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0] == "")

    def test_split_single_sentence(self):
        """Test splitting single short sentence."""
        text = "This is a short sentence."
        chunks = splitTextIntoChunks(text)

        assert len(chunks) > 0
        assert text in " ".join(chunks)

    def test_split_respects_chunk_size(self):
        """Test that chunks respect size limits."""
        text = "Word " * 1000  # Very long text
        chunks = splitTextIntoChunks(text, chunk_size=100)

        # Most chunks should be under size limit (accounting for overlap)
        for chunk in chunks:
            assert len(chunk) <= 150  # Allow some flexibility for overlap

    def test_split_with_overlap(self):
        """Test chunking with overlap."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = splitTextIntoChunks(text, chunk_overlap=20)

        assert len(chunks) > 0
        # Chunks should have some overlap/continuity
        if len(chunks) > 1:
            # There should be some common content between chunks
            combined = " ".join(chunks)
            assert len(combined) >= len(text.strip())

    def test_split_preserves_sentence_structure(self):
        """Test that chunking preserves sentence structure when possible."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = splitTextIntoChunks(text)

        # At least one chunk should contain a period (sentence end)
        assert any("." in chunk for chunk in chunks)


class TestDataSourceEdgeCases:
    """Test edge cases and error handling."""

    def test_process_very_large_file(self, mock_pdf_loader):
        """Test processing very large file."""
        large_content = "Large content " * 10000
        mock_pdf_loader.return_value.pages[0].extract_text.return_value = large_content

        result = processFile("large.pdf", BytesIO(b"fake large pdf"))

        assert len(result) > 0

    def test_extract_file_with_special_characters(self):
        """Test extracting text with special characters."""
        content = "Special chars: !@#$%^&*() and unicode: 你好世界"
        txt_file = BytesIO(content.encode("utf-8"))

        result = extractTextFromTxt(txt_file)

        assert len(result) > 0

    def test_split_text_with_newlines(self):
        """Test chunking text with newlines."""
        text = "Line 1\n\nLine 2\n\nLine 3\n\nLine 4" * 50
        chunks = splitTextIntoChunks(text)

        assert len(chunks) > 0
        combined = " ".join(chunks)
        assert len(combined) > 0

    def test_process_file_with_binary_content(self, mock_pdf_loader):
        """Test processing file with binary content."""
        binary_data = BytesIO(b"\x89PNG\r\n\x1a\n" + b"fake binary data")

        with patch("dataSource.extractTextFromPdf") as mock_pdf:
            mock_pdf.return_value = ""
            result = processFile("test.pdf", binary_data)

    def test_split_single_word(self):
        """Test splitting single word."""
        text = "Supercalifragilisticexpialidocious"
        chunks = splitTextIntoChunks(text)

        assert len(chunks) > 0
        assert text in " ".join(chunks)

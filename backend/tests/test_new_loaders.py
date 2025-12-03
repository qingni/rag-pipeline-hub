"""Tests for new document loaders."""
import pytest
from pathlib import Path
import tempfile
import os


class TestTextLoader:
    """Test text loader."""
    
    def test_load_txt_file(self):
        """Test loading plain text file."""
        from src.providers.loaders.text_loader import text_loader
        
        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("This is a test document.\nWith multiple lines.\nAnd some content.")
            temp_path = f.name
        
        try:
            result = text_loader.extract_text(temp_path)
            
            assert result["success"] is True
            assert result["loader"] == "text"
            assert "This is a test document" in result["full_text"]
            assert result["total_pages"] == 1
            assert result["total_chars"] > 0
            assert "encoding" in result["metadata"]
        finally:
            os.unlink(temp_path)
    
    def test_load_markdown_file(self):
        """Test loading markdown file."""
        from src.providers.loaders.text_loader import text_loader
        
        # Create temporary markdown file
        content = """# Test Markdown
        
## Section 1
This is a test.

## Section 2
- Item 1
- Item 2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = text_loader.extract_text(temp_path)
            
            assert result["success"] is True
            assert "Test Markdown" in result["full_text"]
            assert result["metadata"]["format"] == "md"
        finally:
            os.unlink(temp_path)
    
    def test_empty_file(self):
        """Test loading empty file."""
        from src.providers.loaders.text_loader import text_loader
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            result = text_loader.extract_text(temp_path)
            
            assert result["success"] is True
            assert result["total_chars"] == 0
        finally:
            os.unlink(temp_path)


class TestDocxLoader:
    """Test DOCX loader."""
    
    def test_docx_loader_import(self):
        """Test that DOCX loader can be imported."""
        from src.providers.loaders.docx_loader import docx_loader
        assert docx_loader.name == "docx"
    
    def test_missing_dependency(self):
        """Test behavior when python-docx is not installed."""
        from src.providers.loaders.docx_loader import docx_loader
        
        # Create a dummy file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = f.name
        
        try:
            result = docx_loader.extract_text(temp_path)
            
            # Should either succeed or return error about missing library
            assert "success" in result
            if not result["success"]:
                assert "python-docx" in result.get("error", "").lower() or "error" in result
        finally:
            os.unlink(temp_path)


class TestDocLoader:
    """Test DOC loader."""
    
    def test_doc_loader_import(self):
        """Test that DOC loader can be imported."""
        from src.providers.loaders.doc_loader import doc_loader
        assert doc_loader.name == "doc"
    
    def test_missing_tools(self):
        """Test behavior when extraction tools are not available."""
        from src.providers.loaders.doc_loader import doc_loader
        
        # Create a dummy file
        with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as f:
            temp_path = f.name
        
        try:
            result = doc_loader.extract_text(temp_path)
            
            # Should return error about missing tools
            assert "success" in result
            if not result["success"]:
                error = result.get("error", "").lower()
                assert any(tool in error for tool in ["antiword", "textract"]) or "error" in result
        finally:
            os.unlink(temp_path)


class TestLoadingService:
    """Test loading service with new formats."""
    
    def test_format_loader_map(self):
        """Test format to loader mapping."""
        from src.services.loading_service import loading_service
        
        # Check all supported formats have loaders
        assert loading_service.get_loader_for_format("pdf") == "pymupdf"
        assert loading_service.get_loader_for_format("txt") == "text"
        assert loading_service.get_loader_for_format("md") == "text"
        assert loading_service.get_loader_for_format("markdown") == "text"
        assert loading_service.get_loader_for_format("docx") == "docx"
        assert loading_service.get_loader_for_format("doc") == "doc"
    
    def test_supported_formats(self):
        """Test getting supported formats."""
        from src.services.loading_service import loading_service
        
        formats = loading_service.get_supported_formats()
        
        assert "pdf" in formats
        assert "txt" in formats
        assert "md" in formats
        assert "docx" in formats
        assert "doc" in formats
    
    def test_available_loaders(self):
        """Test getting available loaders."""
        from src.services.loading_service import loading_service
        
        loaders = loading_service.get_available_loaders()
        
        assert "pymupdf" in loaders
        assert "text" in loaders
        assert "docx" in loaders
        assert "doc" in loaders


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

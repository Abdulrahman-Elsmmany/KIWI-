"""
Document parsing utilities for the Kiwi TTS application.

This module provides parsers for different document formats, converting them
to clean text suitable for TTS synthesis.
"""

import re
from pathlib import Path
from typing import Protocol
from abc import ABC, abstractmethod

import markdown
import frontmatter  # type: ignore[import-untyped]

from .utils import FileValidationError, SupportedFileType


class DocumentParser(Protocol):
    """Protocol for document parsers."""
    
    def parse(self, file_path: Path) -> str:
        """Parse document and return clean text."""
        ...


class BaseParser(ABC):
    """Base class for document parsers."""
    
    @abstractmethod
    def parse(self, file_path: Path) -> str:
        """
        Parse document and return clean text suitable for TTS.
        
        Args:
            file_path (Path): Path to the document to parse.
            
        Returns:
            str: Clean text extracted from the document.
            
        Raises:
            FileValidationError: If file cannot be read or parsed.
        """
        pass
    
    def _read_file_content(self, file_path: Path) -> str:
        """
        Read file content with UTF-8 encoding.
        
        Args:
            file_path (Path): Path to the file to read.
            
        Returns:
            str: File content as Unicode string.
            
        Raises:
            FileValidationError: If file cannot be read.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError as e:
            raise FileValidationError(
                f"File encoding error: {file_path}. Expected UTF-8 encoding."
            ) from e
        except OSError as e:
            raise FileValidationError(
                f"Cannot read file: {file_path}. {e}"
            ) from e


class TextFileParser(BaseParser):
    """Parser for plain text files."""
    
    def parse(self, file_path: Path) -> str:
        """
        Parse plain text file.
        
        Args:
            file_path (Path): Path to the text file.
            
        Returns:
            str: Clean text content.
        """
        content = self._read_file_content(file_path)
        
        # Basic text cleaning
        # Remove excessive whitespace and normalize line endings
        content = re.sub(r'\r\n|\r', '\n', content)  # Normalize line endings
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 consecutive newlines
        content = re.sub(r'[ \t]+', ' ', content)  # Normalize spaces and tabs
        
        return content.strip()


class MarkdownParser(BaseParser):
    """Parser for Markdown files with front matter support."""
    
    def __init__(self) -> None:
        """Initialize Markdown parser with extensions."""
        # Configure markdown with useful extensions
        self.md = markdown.Markdown(
            extensions=[
                'extra',      # Tables, fenced code blocks, etc.
                'codehilite', # Syntax highlighting (removes code blocks cleanly)
                'toc',        # Table of contents
            ],
            extension_configs={
                'codehilite': {'use_pygments': False}  # Don't require Pygments
            }
        )
    
    def parse(self, file_path: Path) -> str:
        """
        Parse Markdown file to clean text, handling front matter.
        
        Args:
            file_path (Path): Path to the Markdown file.
            
        Returns:
            str: Clean text extracted from Markdown content.
        """
        content = self._read_file_content(file_path)
        
        # Handle front matter if present
        if content.startswith("---"):
            try:
                post = frontmatter.loads(content)
                markdown_content = post.content
                
                # Optionally include title from front matter
                title = post.metadata.get('title', '')
                if title:
                    markdown_content = f"# {title}\n\n{markdown_content}"
                    
            except Exception:
                # If front matter parsing fails, treat as regular markdown
                markdown_content = content
        else:
            markdown_content = content
        
        # Convert Markdown to HTML
        html = self.md.convert(markdown_content)
        
        # Convert HTML back to clean text
        clean_text = self._html_to_text(html)
        
        # Reset markdown parser for next use
        self.md.reset()
        
        return clean_text
    
    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to clean text suitable for TTS.
        
        Args:
            html (str): HTML content from markdown conversion.
            
        Returns:
            str: Clean text with proper spacing and punctuation.
        """
        # Remove HTML tags but preserve content
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Decode HTML entities
        import html as html_module
        text = html_module.unescape(text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Clean up paragraph breaks
        
        # Add proper sentence spacing for TTS
        text = re.sub(r'\.([A-Z])', r'. \1', text)  # Space after periods
        text = re.sub(r'([.!?])\s*\n', r'\1\n\n', text)  # Paragraph breaks after sentences
        
        return text.strip()


class FrontMatterParser(BaseParser):
    """Parser specifically for extracting and processing front matter."""
    
    def parse(self, file_path: Path) -> str:
        """
        Parse file and extract readable content from front matter.
        
        Args:
            file_path (Path): Path to the file with front matter.
            
        Returns:
            str: Human-readable text from front matter fields.
        """
        content = self._read_file_content(file_path)
        
        if not content.startswith("---"):
            return ""  # No front matter
        
        try:
            post = frontmatter.loads(content)
            
            # Extract readable metadata
            readable_parts = []
            
            # Add title if present
            if 'title' in post.metadata:
                readable_parts.append(f"Title: {post.metadata['title']}")
            
            # Add description if present
            if 'description' in post.metadata:
                readable_parts.append(f"Description: {post.metadata['description']}")
            
            # Add tags if present
            if 'tags' in post.metadata:
                tags = post.metadata['tags']
                if isinstance(tags, list):
                    readable_parts.append(f"Tags: {', '.join(tags)}")
                else:
                    readable_parts.append(f"Tags: {tags}")
            
            return ". ".join(readable_parts) + "." if readable_parts else ""
            
        except Exception:
            return ""  # If parsing fails, return empty string


class ParserFactory:
    """Factory for creating appropriate parsers based on file type."""
    
    @staticmethod
    def get_parser(file_extension: str) -> DocumentParser:
        """
        Get appropriate parser for file extension.
        
        Args:
            file_extension (str): File extension (e.g., '.md', '.txt').
            
        Returns:
            DocumentParser: Parser instance for the file type.
            
        Raises:
            ValueError: If file extension is not supported.
        """
        extension = file_extension.lower()
        
        if extension == SupportedFileType.MARKDOWN.value:
            return MarkdownParser()
        elif extension == SupportedFileType.TEXT.value:
            return TextFileParser()
        else:
            raise ValueError(
                f"Unsupported file extension: {extension}. "
                f"Supported: {[ft.value for ft in SupportedFileType]}"
            )
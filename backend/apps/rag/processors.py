# /backend/apps/rag/processors.py

"""
Document processors for extracting text from various file formats
"""
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF text extraction and processing"""

    def __init__(self):
        self.min_text_length = 50  # Minimum text length to consider valid
        self.section_patterns = [
            r"^([A-Z][A-Z\s]{2,30})$",  # ALL CAPS headers
            r"^\d+\.?\s+[A-Z].*",  # Numbered sections (1. Introduction)
            r"^[A-Z][a-z]+(?:\s[A-Z][a-z]+)*:",  # Title Case: headers
            r"^\*{1,3}[A-Z].*\*{1,3}$",  # *Bold headers*
        ]

    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and structure from PDF

        Args:
            file_path: Path to PDF file

        Returns:
            Dict containing extracted data with structure
        """
        try:
            # Try PyMuPDF first (better for structured extraction)
            try:
                return self._extract_with_pymupdf(file_path)
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed, trying pdfplumber: {e}")
                return self._extract_with_pdfplumber(file_path)

        except Exception as e:
            logger.error(f"All PDF extraction methods failed for {file_path}: {e}")
            raise

    def _extract_with_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text using PyMuPDF (better for structure)"""
        doc = fitz.open(file_path)
        pages_data = []

        try:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Get text blocks with position info
                blocks = page.get_text("dict")
                page_text = page.get_text()

                # Extract sections based on text structure
                sections = self._extract_sections_from_text(page_text)

                page_data = {
                    "page_number": page_num + 1,
                    "content": page_text.strip(),
                    "sections": sections,
                    "metadata": {
                        "extraction_method": "pymupdf",
                        "char_count": len(page_text),
                        "block_count": len(blocks.get("blocks", [])),
                    },
                }

                if len(page_text.strip()) >= self.min_text_length:
                    pages_data.append(page_data)

        finally:
            doc.close()

        return {
            "pages": pages_data,
            "page_count": len(pages_data),
            "total_chars": sum(len(p["content"]) for p in pages_data),
            "extraction_method": "pymupdf",
        }

    def _extract_with_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """Extract text using pdfplumber (better for tables)"""
        pages_data = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()

                if not page_text or len(page_text.strip()) < self.min_text_length:
                    continue

                # Extract tables if present
                tables = page.extract_tables()
                table_text = ""
                if tables:
                    table_text = self._format_tables(tables)

                # Combine text and tables
                combined_text = page_text
                if table_text:
                    combined_text += "\n\n" + table_text

                # Extract sections
                sections = self._extract_sections_from_text(combined_text)

                page_data = {
                    "page_number": page_num + 1,
                    "content": combined_text.strip(),
                    "sections": sections,
                    "metadata": {
                        "extraction_method": "pdfplumber",
                        "char_count": len(combined_text),
                        "table_count": len(tables),
                    },
                }

                pages_data.append(page_data)

        return {
            "pages": pages_data,
            "page_count": len(pages_data),
            "total_chars": sum(len(p["content"]) for p in pages_data),
            "extraction_method": "pdfplumber",
        }

    def _extract_sections_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract sections from text based on patterns"""
        if not text:
            return []

        lines = text.split("\n")
        sections = []
        current_section = {"title": "", "content": ""}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line is a section header
            is_header = self._is_section_header(line)

            if is_header:
                # Save previous section if it has content
                if current_section["content"]:
                    sections.append(current_section.copy())

                # Start new section
                current_section = {"title": line, "content": ""}
            else:
                # Add to current section content
                if current_section["content"]:
                    current_section["content"] += "\n"
                current_section["content"] += line

        # Add last section
        if current_section["content"]:
            sections.append(current_section)

        # If no sections found, create one section with all content
        if not sections:
            sections = [{"title": "", "content": text}]

        return sections

    def _is_section_header(self, line: str) -> bool:
        """Check if line is likely a section header"""
        if not line or len(line) > 100:  # Too long to be a header
            return False

        for pattern in self.section_patterns:
            if re.match(pattern, line):
                return True

        # Additional heuristics
        if (
            len(line.split()) <= 6  # Short
            and line[0].isupper()  # Starts with capital
            and not line.endswith(".")  # Doesn't end with period
            and ":" in line[-3:]
        ):  # Ends with colon
            return True

        return False

    def _format_tables(self, tables: List[List[List[str]]]) -> str:
        """Format extracted tables as text"""
        formatted_tables = []

        for i, table in enumerate(tables):
            if not table:
                continue

            table_lines = [f"Table {i + 1}:"]

            for row in table:
                if row:  # Skip empty rows
                    # Clean and join cells
                    cleaned_cells = [str(cell).strip() if cell else "" for cell in row]
                    table_lines.append(" | ".join(cleaned_cells))

            formatted_tables.append("\n".join(table_lines))

        return "\n\n".join(formatted_tables)

    def validate_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Validate PDF file and get basic info

        Args:
            file_path: Path to PDF file

        Returns:
            Dict with validation results
        """
        try:
            if not os.path.exists(file_path):
                return {"valid": False, "error": "File not found"}

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {"valid": False, "error": "Empty file"}

            # Try to open with PyMuPDF
            doc = fitz.open(file_path)

            result = {
                "valid": True,
                "page_count": len(doc),
                "file_size": file_size,
                "is_encrypted": doc.is_encrypted,
                "metadata": doc.metadata,
            }

            doc.close()
            return result

        except Exception as e:
            return {"valid": False, "error": str(e)}


class TextProcessor:
    """Process plain text files"""

    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from plain text file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple section detection for text files
            sections = [{"title": "", "content": content}]

            page_data = {
                "page_number": 1,
                "content": content,
                "sections": sections,
                "metadata": {"extraction_method": "text", "char_count": len(content)},
            }

            return {
                "pages": [page_data],
                "page_count": 1,
                "total_chars": len(content),
                "extraction_method": "text",
            }

        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise


def get_processor_for_file(file_path: str):
    """Get appropriate processor based on file extension"""
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return PDFProcessor()
    elif suffix in [".txt", ".md"]:
        return TextProcessor()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

# apps/adapters/parsing/pymupdf_parser.py
"""
PyMuPDF Parser Adapter

Implements IDocumentParser using PyMuPDF (fitz) for PDF extraction.
"""
import logging
from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF

from apps.domain.models import DocumentContent, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class PyMuPDFParser:
    """
    PDF parser using PyMuPDF library

    Fast and reliable PDF text extraction.
    """

    def __init__(self):
        """Initialize PyMuPDF parser"""
        self.supported_types = ["pdf"]

    def parse(self, file_path: str) -> DocumentContent:
        """
        Extract text from PDF file

        Args:
            file_path: Path to PDF file

        Returns:
            DocumentContent with extracted text

        Raises:
            NotFoundError: If file doesn't exist
            ValidationError: If file is invalid
        """
        # Validate file exists
        path = Path(file_path)
        if not path.exists():
            raise NotFoundError(f"File not found: {file_path}")

        if not path.suffix.lower() == ".pdf":
            raise ValidationError(f"Not a PDF file: {file_path}")

        try:
            logger.info(f"Parsing PDF: {path.name}")

            # Open PDF
            doc = fitz.open(file_path)

            pages = []
            total_chars = 0

            # Extract text from each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()

                # Skip empty pages
                if not text.strip():
                    continue

                # Extract sections (simple heuristic)
                sections = self._extract_sections(text)

                page_data = {
                    "page_number": page_num + 1,
                    "content": text.strip(),
                    "sections": sections,
                    "metadata": {
                        "char_count": len(text),
                        "extraction_method": "pymupdf",
                    },
                }

                pages.append(page_data)
                total_chars += len(text)

            doc.close()

            logger.info(
                f"Extracted {len(pages)} pages, "
                f"{total_chars} characters from {path.name}"
            )

            return DocumentContent(
                pages=pages,
                page_count=len(pages),
                total_chars=total_chars,
                extraction_method="pymupdf",
                metadata={"filename": path.name, "file_size": path.stat().st_size},
            )

        except fitz.FileDataError as e:
            logger.error(f"Invalid PDF file: {e}")
            raise ValidationError(f"Invalid PDF: {e}")

        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            raise ValidationError(f"Parsing failed: {e}")

    def supports(self, file_type: str) -> bool:
        """
        Check if file type is supported

        Args:
            file_type: File extension

        Returns:
            True if supported
        """
        return file_type.lower() in self.supported_types

    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Extract sections from page text

        Simple heuristic: Look for ALL CAPS lines as headers.

        Args:
            text: Page text

        Returns:
            List of section dicts
        """
        import re

        sections = []
        current_section = {"title": "", "content": ""}

        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line looks like a header (ALL CAPS, short)
            if line.isupper() and len(line.split()) <= 10 and len(line) > 3:

                # Save previous section
                if current_section["content"]:
                    sections.append(current_section.copy())

                # Start new section
                current_section = {"title": line, "content": ""}
            else:
                # Add to current section
                if current_section["content"]:
                    current_section["content"] += "\n"
                current_section["content"] += line

        # Add last section
        if current_section["content"]:
            sections.append(current_section)

        # If no sections found, treat all as one section
        if not sections:
            sections = [{"title": "", "content": text}]

        return sections

# apps/domain/ports/parser.py

"""
Document Parser Port - Interface for extracting text from files

This port defines the contract for document parsing.
"""

from typing import Protocol

from apps.domain.models import DocumentContent


class IDocumentParser(Protocol):
    """
    Interface for document parsers

    Implementations must extract text and structure from documents.
    """

    def parse(self, file_path: str) -> DocumentContent:
        """
        Extract content from a document file

        Args:
            file_path: Absolute path to the document file

        Returns:
            DocumentContent object with extracted text and metadata

        Raises:
            ValidationError: If file is not valid or corrupted
            NotFoundError: If file doesn't exist

        Example:
            parser = PyMuPDFParser()
            content = parser.parse("/path/to/doc.pdf")
            content.page_count
            25
        """
        ...

    def supports(self, file_type: str) -> bool:
        """
        Check if this parser supports a file type

        Args:
            file_type: File extension (e.g., 'pdf', 'txt', 'docx')

        Returns:
            True if file type is supported, False otherwise

        Example:
            parser.supports('pdf')
            True
            parser.supports('xlsx')
            False
        """
        ...

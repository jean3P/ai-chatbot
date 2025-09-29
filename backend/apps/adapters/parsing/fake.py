# apps/adapters/parsing/fake.py
"""
Fake Document Parser for testing
"""
from apps.domain.models import DocumentContent


class FakeParser:
    """
    Fake parser that returns predetermined content
    """

    def __init__(self, content: DocumentContent = None):
        """
        Initialize fake parser

        Args:
            content: DocumentContent to return
        """
        self.content = content or DocumentContent(
            pages=[{
                'page_number': 1,
                'content': 'Test content',
                'sections': [{'title': '', 'content': 'Test content'}],
                'metadata': {}
            }],
            page_count=1,
            total_chars=12,
            extraction_method='fake'
        )
        self.parse_called = False

    def parse(self, file_path: str) -> DocumentContent:
        """Return predetermined content"""
        self.parse_called = True
        return self.content

    def supports(self, file_type: str) -> bool:
        """Support all file types"""
        return True

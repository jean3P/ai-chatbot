# Document Parser Adapters

## Purpose
Parser adapters implement the `IDocumentParser` port for extracting text from various document formats.

## Interface

```python
class IDocumentParser(Protocol):
    def parse(self, file_path: str) -> DocumentContent:
        """Extract text and structure from document"""
        ...
    
    def supports(self, file_type: str) -> bool:
        """Check if parser supports file type"""
        ...
```

## Implementations

### 1. PyMuPDFParser (Primary)
- **Library**: PyMuPDF (fitz)
- **Speed**: Fast (~100ms per page)
- **Quality**: Good structure extraction
- **Use case**: Primary PDF parser

**Configuration:**
```python
parser = PyMuPDFParser()
```

**Pros:**
- Fast processing
- Good text structure
- Extracts metadata
- Handles images

**Cons:**
- Some PDFs have extraction issues
- May miss table data

### 2. PDFPlumberParser (Fallback)
- **Library**: pdfplumber
- **Speed**: Slower (~200ms per page)
- **Quality**: Excellent table extraction
- **Use case**: Backup when PyMuPDF fails

**Configuration:**
```python
parser = PDFPlumberParser()
```

**Pros:**
- Excellent table extraction
- Good for forms
- Detailed layout info

**Cons:**
- Slower than PyMuPDF
- Higher memory usage

### 3. FakeParser (Testing)
- **Speed**: Instant
- **Use case**: Unit tests

**Configuration:**
```python
parser = FakeParser(
    content=DocumentContent(
        pages=[...],
        page_count=5,
        total_chars=1000,
        extraction_method="fake"
    )
)
```

## Usage Example

```python
# Try primary parser, fallback to secondary
def parse_pdf(file_path: str) -> DocumentContent:
    try:
        parser = PyMuPDFParser()
        return parser.parse(file_path)
    except Exception as e:
        logger.warning(f"PyMuPDF failed, trying pdfplumber: {e}")
        parser = PDFPlumberParser()
        return parser.parse(file_path)
```

## Testing

```python
def test_pymupdf_parser():
    """Test PDF parsing"""
    parser = PyMuPDFParser()
    
    content = parser.parse("tests/fixtures/test.pdf")
    
    assert content.page_count > 0
    assert content.total_chars > 0
    assert len(content.pages) == content.page_count

def test_fake_parser():
    """Test with fake parser"""
    parser = FakeParser(
        content=DocumentContent(
            pages=[{'page_number': 1, 'content': 'Test'}],
            page_count=1,
            total_chars=4,
            extraction_method="fake"
        )
    )
    
    content = parser.parse("any-path.pdf")
    
    assert content.page_count == 1
    assert content.pages[0]['content'] == 'Test'
```

## Migration Notes

Current parsing code in `apps/rag/processors.py` will be refactored:
- Extract PDF extraction logic
- Implement IDocumentParser interface
- Add proper error handling
- Remove tight coupling to Django models
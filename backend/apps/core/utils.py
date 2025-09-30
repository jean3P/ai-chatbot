# backend/apps/core/utils.py
"""
Utility functions for the core app
"""
import hashlib
import re
from typing import Any, Dict, List


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove special characters but keep basic punctuation
    text = re.sub(r"[^\w\s\.\,\?\!\-\:\;]", "", text)

    return text.strip()


def chunk_text(text: str, max_size: int = 1200, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks

    Args:
        text (str): Text to chunk
        max_size (int): Maximum chunk size in characters
        overlap (int): Overlap between chunks

    Returns:
        List[str]: List of text chunks
    """
    if len(text) <= max_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_size

        if end >= len(text):
            chunks.append(text[start:])
            break

        # Try to break at sentence boundary
        chunk = text[start:end]
        last_period = chunk.rfind(".")
        last_newline = chunk.rfind("\n")

        break_point = max(last_period, last_newline)

        if (
            break_point > start + max_size // 2
        ):  # Only break if we're not too close to start
            end = start + break_point + 1

        chunks.append(text[start:end])
        start = end - overlap

    return [chunk.strip() for chunk in chunks if chunk.strip()]


def generate_chunk_id(text: str, document_id: str = None) -> str:
    """Generate unique ID for a text chunk"""
    content = f"{document_id or 'unknown'}:{text[:100]}"
    return hashlib.md5(content.encode()).hexdigest()


def extract_citations(text: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract citations from generated text based on sources"""
    citations = []

    for i, source in enumerate(sources):
        # Simple citation extraction - in production, you'd want more sophisticated matching
        if any(keyword in text.lower() for keyword in source.get("keywords", [])):
            citations.append(
                {
                    "id": f"citation_{i}",
                    "document": source.get("document", "Unknown"),
                    "page": source.get("page", 1),
                    "section": source.get("section"),
                    "text": source.get("text", "")[:200] + "...",
                }
            )

    return citations


def format_conversation_context(
    messages: List[Dict[str, Any]], max_context_length: int = 2000
) -> str:
    """Format conversation history into context string"""
    context_parts = []
    total_length = 0

    # Start from most recent messages
    for message in reversed(messages):
        role = message.get("role", "user")
        content = message.get("content", "")

        formatted = f"{role.title()}: {content}\n"

        if total_length + len(formatted) > max_context_length:
            break

        context_parts.insert(0, formatted)
        total_length += len(formatted)

    return "".join(context_parts)


def validate_openrouter_key(api_key: str) -> bool:
    """Validate OpenRouter API key format"""
    if not api_key:
        return False

    # OpenRouter keys start with 'sk-or-v1-'
    return api_key.startswith("sk-or-v1-") and len(api_key) > 20

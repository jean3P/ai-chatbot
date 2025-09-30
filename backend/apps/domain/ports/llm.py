# apps/domain/ports/llm.py

"""
LLM Provider Port - Interface for text generation

This port defines the contract for LLM providers.
Any adapter that implements these methods can be used by the domain.
"""

from typing import Dict, Iterator, List, Protocol


class ILLMProvider(Protocol):
    """
    Interface for Large Language Model providers

    Implementations must provide text generation capabilities
    with both batch and streaming modes.
    """

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a completion for the given messages

        Args:
            messages: List of message dicts with 'role' and 'content' keys
                Example: [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"}
                ]
            **kwargs: Optional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text response

        Raises:
            LLMProviderError: If generation fails
        """
        ...

    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """
        Stream a completion for the given messages

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Optional parameters

        Yields:
            Text chunks as they are generated

        Raises:
            LLMProviderError: If streaming fails

        Note:
            Streaming is optional for Phase 1. Can raise NotImplementedError.
        """
        ...

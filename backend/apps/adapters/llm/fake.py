# apps/adapters/llm/fake.py
"""
Fake LLM Provider for testing

Provides deterministic responses without API calls.
"""
from typing import List, Dict, Iterator


class FakeLLM:
    """
    Fake LLM implementation for unit testing

    Returns predetermined responses instantly without API calls.
    """

    def __init__(self, response: str = "This is a test response"):
        """
        Initialize fake LLM

        Args:
            response: The response to return for all generate() calls
        """
        self.response = response
        self.generate_called = False
        self.stream_called = False
        self.last_messages = None

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Return predetermined response

        Args:
            messages: Input messages (stored but not used)
            **kwargs: Ignored

        Returns:
            The predetermined response string
        """
        self.generate_called = True
        self.last_messages = messages
        return self.response

    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """
        Stream predetermined response word by word

        Args:
            messages: Input messages
            **kwargs: Ignored

        Yields:
            Words from the response
        """
        self.stream_called = True
        self.last_messages = messages

        # Split response into words and yield
        words = self.response.split()
        for word in words:
            yield word + " "

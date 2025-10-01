# apps/adapters/llm/openrouter.py
"""
OpenRouter LLM Provider Adapter

Implements ILLMProvider using OpenRouter API for accessing multiple LLM models.
"""
import logging
from typing import Dict, Iterator, List

import openai

from apps.domain.models import LLMProviderError

logger = logging.getLogger(__name__)


class OpenRouterLLM:
    """
    OpenRouter API adapter for LLM access

    Provides access to multiple LLM models through unified API.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ):
        """
        Initialize OpenRouter LLM client

        Args:
            api_key: OpenRouter API key
            base_url: API base URL
            model: Model identifier
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
        """
        if not api_key:
            raise ValueError("OpenRouter API key is required")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize OpenAI client (compatible with OpenRouter)
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

        # Track usage
        self.tokens_used = {"input": 0, "output": 0, "total": 0}
        self.last_response = None

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate completion using OpenRouter

        Args:
            messages: List of message dicts
            **kwargs: Optional overrides (temperature, max_tokens)

        Returns:
            Generated text

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            # Override defaults with kwargs if provided
            temperature = kwargs.get("temperature", self.temperature)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)

            logger.debug(
                f"Generating completion with model={self.model}, "
                f"temp={temperature}, max_tokens={max_tokens}"
            )

            # Call API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            # Store response for inspection
            self.last_response = response

            # Track token usage
            if hasattr(response, "usage") and response.usage:
                self.tokens_used = {
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.total_tokens,
                }
                logger.info(f"Tokens used: {self.tokens_used['total']}")

                # Calculate cost
                from apps.infrastructure.pricing import calculate_cost
                cost = calculate_cost(
                    self.tokens_used["input"],
                    self.tokens_used["output"],
                    self.model
                )
                self.tokens_used["cost_usd"] = cost

                logger.info(
                    f"Tokens: {self.tokens_used['total']} "
                    f"(${cost:.4f})"
                )
            # Extract content
            content = response.choices[0].message.content

            if not content:
                raise LLMProviderError("Empty response from LLM")

            return content

        except openai.RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise LLMProviderError(f"Rate limit exceeded: {e}")

        except openai.APIError as e:
            logger.error(f"OpenRouter API error: {e}")
            raise LLMProviderError(f"API error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            raise LLMProviderError(f"Generation failed: {e}")

    def get_last_usage(self) -> dict:
        """Get token usage and cost from last call"""
        return self.tokens_used

    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """
        Stream completion using OpenRouter

        Args:
            messages: List of message dicts
            **kwargs: Optional overrides

        Yields:
            Text chunks as they are generated

        Raises:
            LLMProviderError: If streaming fails
        """
        try:
            temperature = kwargs.get("temperature", self.temperature)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)

            logger.debug(f"Streaming completion with model={self.model}")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            raise LLMProviderError(f"Streaming failed: {e}")

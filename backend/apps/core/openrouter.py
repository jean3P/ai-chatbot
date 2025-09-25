# backend/apps/core/openrouter.py
"""
OpenRouter API client for free AI models
"""
import openai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for OpenRouter API with free models"""

    def __init__(self):
        self.client = openai.OpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.embedding_model = settings.DEFAULT_EMBEDDING_MODEL
        self.llm_model = settings.DEFAULT_LLM_MODEL
        self.multilingual_model = settings.MULTILINGUAL_LLM_MODEL

    def generate_embeddings(self, texts, model=None):
        """
        Generate embeddings for a list of texts

        Args:
            texts (list): List of text strings
            model (str): Model name (optional)

        Returns:
            list: List of embedding vectors
        """
        try:
            model = model or self.embedding_model

            response = self.client.embeddings.create(
                model=model,
                input=texts
            )

            embeddings = [item.embedding for item in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings using {model}")

            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def generate_answer(self, messages, model=None, stream=False, max_tokens=1000):
        """
        Generate chat completion

        Args:
            messages (list): List of message dictionaries
            model (str): Model name (optional)
            stream (bool): Whether to stream the response
            max_tokens (int): Maximum tokens to generate

        Returns:
            str or generator: Response text or streaming generator
        """
        try:
            model = model or self.llm_model

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=max_tokens,
                stream=stream
            )

            if stream:
                return self._stream_response(response)
            else:
                content = response.choices[0].message.content
                logger.info(f"Generated answer using {model}")
                return content

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def _stream_response(self, response):
        """Handle streaming response"""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def get_available_models(self):
        """Get list of available models"""
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []


# Global client instance
openrouter_client = OpenRouterClient()

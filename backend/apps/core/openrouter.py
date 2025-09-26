# apps/core/openrouter.py

import logging
from typing import Any, List, Optional

import openai
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for OpenRouter API with free models"""

    def __init__(self):
        self.base_url: str = getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.api_key: str = getattr(settings, "OPENROUTER_API_KEY", "")

        # Use consistent embedding model
        self.embedding_model: str = getattr(settings, "DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small")
        self.llm_model: str = getattr(settings, "DEFAULT_LLM_MODEL", "gpt-4o-mini")
        self.multilingual_model: str = getattr(settings, "MULTILINGUAL_LLM_MODEL", self.llm_model)

        # Local fallback - use same model consistently
        self.local_fallback_model: Optional[str] = getattr(
            settings, "LOCAL_EMBEDDING_FALLBACK_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )

        self.client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        # Track which embedding model we're actually using
        self._current_embedding_model = None
        self._use_local_fallback = False

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is empty!")
            self._use_local_fallback = True
        if not self.embedding_model:
            logger.warning("DEFAULT_EMBEDDING_MODEL is not set!")

    def generate_embeddings(self, texts: List[str], model: str | None = None) -> List[List[float]]:
        model = model or self.embedding_model
        if not texts:
            return []
        texts = ["" if t is None else str(t) for t in texts]

        logger.info(f"Embeddings: model={model} base_url={self.base_url} batch_size={len(texts)}")

        # If we've determined to use local fallback, go straight there
        if self._use_local_fallback:
            return self._generate_local_embeddings(texts)

        # 1) Try OpenRouter first, but with better error handling
        try:
            # Use requests directly for better control
            url = f"{self.base_url}/embeddings"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://localhost"),
                "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "swisson-ai-chatbot"),
            }
            payload = {"model": model, "input": texts}

            r = requests.post(
                url,
                headers=headers,
                json=payload,  # Use json parameter instead of manual encoding
                timeout=60,
                allow_redirects=False,
            )

            if 300 <= r.status_code < 400:
                logger.error(f"OpenRouter redirected (status {r.status_code}) to: {r.headers.get('Location')}")
                raise RuntimeError("Embeddings endpoint redirected")

            # Check if we got a successful response
            if r.status_code == 200:
                ctype = r.headers.get("Content-Type", "")
                if "application/json" in ctype:
                    data = r.json()
                    vectors = self._extract_embeddings_generic(data)
                    if len(vectors) == len(texts):
                        self._current_embedding_model = model
                        logger.info(f"OpenRouter embeddings successful: {len(vectors)} vectors")
                        return vectors
                    else:
                        logger.warning(f"Vector count mismatch: expected {len(texts)}, got {len(vectors)}")
                else:
                    logger.error(f"OpenRouter returned non-JSON ({ctype})")
            else:
                logger.error(f"OpenRouter API error: {r.status_code} - {r.text[:500]}")

        except Exception as e:
            logger.error(f"OpenRouter embeddings failed: {e}")

        # 2) Fallback to local embeddings
        logger.warning("Falling back to local embeddings")
        self._use_local_fallback = True
        return self._generate_local_embeddings(texts)

    def _generate_local_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local SentenceTransformers model"""
        try:
            if not self.local_fallback_model:
                raise RuntimeError("No local fallback model configured")

            logger.info(f"Using local embedding model: {self.local_fallback_model}")

            # Import here to avoid dependency issues
            from sentence_transformers import SentenceTransformer

            # Load or reuse model
            if not hasattr(self, '_local_model'):
                self._local_model = SentenceTransformer(self.local_fallback_model)

            vectors = self._local_model.encode(texts, normalize_embeddings=True).tolist()
            self._current_embedding_model = self.local_fallback_model
            logger.info(f"Local embeddings OK: {len(vectors)} vectors")
            return vectors

        except Exception as e:
            logger.error(f"Local embedding fallback failed: {e}")
            raise RuntimeError("All embedding strategies failed")

    def get_current_embedding_model(self) -> str:
        """Get the currently active embedding model"""
        return self._current_embedding_model or self.embedding_model

    def _extract_embeddings_generic(self, resp: Any) -> List[List[float]]:
        # Handle OpenAI SDK response format
        if hasattr(resp, "data"):
            try:
                return [item.embedding for item in resp.data]
            except Exception:
                try:
                    return [item["embedding"] for item in resp.data]
                except Exception as e:
                    raise ValueError(f"Cannot read .data from SDK response: {e}")

        # Handle dict response
        if isinstance(resp, dict):
            if "data" in resp and isinstance(resp["data"], list):
                out = []
                for item in resp["data"]:
                    if isinstance(item, dict) and "embedding" in item:
                        out.append(item["embedding"])
                    else:
                        raise ValueError(f"Item missing 'embedding' field: {item}")
                return out
            if "embeddings" in resp:
                return resp["embeddings"]

        # Handle list response
        if isinstance(resp, list):
            if resp and isinstance(resp[0], dict) and "embedding" in resp[0]:
                return [d["embedding"] for d in resp]
            return resp

        raise ValueError(f"Cannot extract embeddings from response type: {type(resp)}")

    # Chat methods remain the same
    def generate_answer(self, messages, model=None, stream=False, max_tokens=1000):
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
            content = response.choices[0].message.content
            logger.info(f"Generated answer using {model}")
            return content
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def _stream_response(self, response):
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def get_available_models(self):
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []


openrouter_client = OpenRouterClient()

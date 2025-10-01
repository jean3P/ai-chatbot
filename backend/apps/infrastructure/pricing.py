# apps/infrastructure/pricing.py
"""
LLM Model Pricing Configuration

Prices in USD per 1M tokens (updated as of 2025)
"""

MODEL_PRICING = {
    # OpenAI Models
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
    },
    "gpt-4o-mini": {
        "input": 0.150,
        "output": 0.600,
    },
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00,
    },
    # Anthropic Claude
    "claude-3-5-sonnet": {
        "input": 3.00,
        "output": 15.00,
    },
    "claude-3-haiku": {
        "input": 0.25,
        "output": 1.25,
    },
    # Meta Llama
    "meta-llama/llama-3.2-3b-instruct": {
        "input": 0.06,
        "output": 0.06,
    },
    "meta-llama/llama-3-8b-instruct": {
        "input": 0.18,
        "output": 0.18,
    },
    # Mistral
    "mistralai/mistral-7b-instruct": {
        "input": 0.20,
        "output": 0.20,
    },
    # Embeddings
    "text-embedding-3-small": {
        "input": 0.020,
        "output": 0.0,  # Embeddings don't have output cost
    },
    "text-embedding-3-large": {
        "input": 0.130,
        "output": 0.0,
    },
}


def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """
    Calculate cost in USD for an LLM call

    Args:
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        model: Model identifier

    Returns:
        Cost in USD
    """
    pricing = MODEL_PRICING.get(model)

    if not pricing:
        # Unknown model - log warning but don't fail
        import logging

        logging.warning(f"Unknown model for pricing: {model}")
        return 0.0

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def get_model_info(model: str) -> dict:
    """Get pricing info for a model"""
    pricing = MODEL_PRICING.get(model)

    if not pricing:
        return {
            "model": model,
            "input_price": 0.0,
            "output_price": 0.0,
            "known": False,
        }

    return {
        "model": model,
        "input_price": pricing["input"],
        "output_price": pricing["output"],
        "known": True,
    }

# LLM Adapters

## Purpose
LLM adapters implement the `ILLMProvider` port for text generation with different LLM providers.

## Interface

```python
class ILLMProvider(Protocol):
    def generate(self, messages: List[Dict]) -> str:
        """Generate completion for messages"""
        ...
    
    def stream(self, messages: List[Dict]) -> Iterator[str]:
        """Stream completion tokens"""
        ...
```

## Implementations

### 1. OpenRouterLLM
- **Purpose**: Access multiple models through unified API
- **Cost**: Variable by model
- **Latency**: ~1-2 seconds
- **Use case**: Production default

**Configuration:**
```python
llm = OpenRouterLLM(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    model="gpt-4o-mini"
)
```

### 2. AnthropicLLM (Planned)
- **Purpose**: Direct Claude API access
- **Cost**: $0.003/1K tokens (Claude Sonnet)
- **Latency**: ~0.8 seconds
- **Use case**: High-quality answers

### 3. OpenAILLM (Planned)
- **Purpose**: GPT models
- **Cost**: $0.0001/1K tokens (GPT-4o-mini)
- **Latency**: ~0.5 seconds
- **Use case**: Cost optimization

### 4. FakeLLM
- **Purpose**: Testing/development
- **Cost**: $0
- **Latency**: Instant
- **Use case**: Unit tests

**Configuration:**
```python
llm = FakeLLM(response="Test answer")
```

## Error Handling

```python
try:
    response = llm.generate(messages)
except RateLimitError:
    # Wait and retry
    time.sleep(1)
    response = llm.generate(messages)
except APIError as e:
    # Log and fallback
    logger.error(f"LLM API error: {e}")
    raise LLMProviderError(f"Failed to generate: {e}")
```

## Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError))
)
def generate(self, messages):
    return self.client.chat.completions.create(...)
```

## Circuit Breaker (Planned Phase 2)

```python
@circuit_breaker(failure_threshold=5, timeout=30)
def generate(self, messages):
    # Automatically opens circuit after failures
    return self.client.generate(messages)
```

## Token Tracking

```python
class OpenRouterLLM:
    def generate(self, messages):
        response = self.client.chat.completions.create(...)
        
        # Track usage
        self.tokens_used = {
            'input': response.usage.prompt_tokens,
            'output': response.usage.completion_tokens,
            'total': response.usage.total_tokens
        }
        
        return response.choices[0].message.content
```

## Testing

```python
def test_openrouter_adapter_generates_response():
    """Integration test with real API"""
    adapter = OpenRouterLLM(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="gpt-4o-mini"
    )
    
    messages = [{"role": "user", "content": "Say hello"}]
    response = adapter.generate(messages)
    
    assert isinstance(response, str)
    assert len(response) > 0

def test_fake_llm_for_unit_tests():
    """Unit test with fake"""
    fake_llm = FakeLLM(response="Hello, world!")
    
    messages = [{"role": "user", "content": "Say hello"}]
    response = fake_llm.generate(messages)
    
    assert response == "Hello, world!"
```

## Migration Notes

Current `apps/core/openrouter.py` will be refactored into this adapter:
- Extract API client code
- Add proper error handling
- Implement ILLMProvider interface
- Remove global singleton pattern
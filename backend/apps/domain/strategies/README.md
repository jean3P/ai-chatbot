# RAG Strategies

## Purpose
Strategies implement different RAG (Retrieval-Augmented Generation) approaches. All strategies implement the same interface, enabling seamless experimentation and A/B testing.

## Strategy Pattern

```python
class IRagStrategy(Protocol):
    """All RAG methods implement this interface"""
    
    def retrieve(
        self,
        query: str,
        history: List[Message],
        filters: Optional[Dict] = None
    ) -> List[Chunk]:
        """Find relevant document chunks"""
        ...
    
    def build_prompt(
        self,
        query: str,
        chunks: List[Chunk],
        history: List[Message],
        language: str
    ) -> List[Dict]:
        """Construct LLM messages with context"""
        ...
    
    def extract_citations(
        self,
        response: str,
        chunks: List[Chunk]
    ) -> List[Citation]:
        """Extract document citations from response"""
        ...
    
    def generate_answer(
        self,
        query: str,
        history: List[Message],
        language: str = "en"
    ) -> Answer:
        """End-to-end: retrieve → prompt → generate → cite"""
        ...
```

## Planned Strategies

### Phase 1: Baseline (MVP)
- **Dense retrieval only** (cosine similarity)
- Simple prompt template
- Basic citation extraction
- Target: 85% recall@10

### Phase 2: Hybrid (Post-MVP)
- **Dense + BM25** (keyword + semantic)
- Fusion ranking (Reciprocal Rank Fusion)
- Improved citation matching
- Target: 90% recall@10

### Phase 3: Rerank (Optimization)
- Two-stage retrieval
- Cross-encoder reranking
- Advanced prompt engineering
- Target: 93% recall@10

## Benefits of Strategy Pattern

### 1. Experimentation
```python
# Switch strategies via configuration
config = {
    'strategy': 'hybrid',  # or 'baseline', 'rerank'
    'llm_model': 'gpt-4o-mini'
}
```

### 2. A/B Testing
```python
# Route 10% traffic to new strategy
if random.random() < 0.1:
    strategy = hybrid_strategy
else:
    strategy = baseline_strategy
```

### 3. Comparison
```python
# Compare performance systematically
for strategy in [baseline, hybrid, rerank]:
    results = evaluate(strategy, test_queries)
    print(f"{strategy.name}: {results.recall@10}")
```

## Implementation Example

```python
class BaselineStrategy:
    """Simple dense retrieval + vanilla prompt"""
    
    def __init__(
        self,
        retriever: IRetriever,
        llm: ILLMProvider,
        prompt_template: PromptTemplate
    ):
        self._retriever = retriever
        self._llm = llm
        self._template = prompt_template
    
    def generate_answer(self, query, history, language):
        # 1. Retrieve
        chunks = self.retrieve(query, history)
        
        # 2. Build prompt
        messages = self.build_prompt(query, chunks, history, language)
        
        # 3. Generate
        response = self._llm.generate(messages)
        
        # 4. Extract citations
        citations = self.extract_citations(response, chunks)
        
        return Answer(
            content=response,
            citations=citations,
            sources=chunks,
            method="baseline"
        )
```

## Testing Strategies

Each strategy should have comprehensive tests:

```python
def test_baseline_retrieves_relevant_chunks():
    fake_retriever = FakeRetriever(results=[chunk1, chunk2])
    strategy = BaselineStrategy(fake_retriever, fake_llm, template)
    
    chunks = strategy.retrieve("DMX splitter", history=[])
    
    assert len(chunks) > 0
    assert chunks[0].score > chunks[1].score  # Sorted by relevance
```

## Configuration

Strategies are configured in `infrastructure/config.py`:

```python
STRATEGY_CONFIG = {
    'baseline': {
        'retrieval': {
            'top_k': 10,
            'threshold': 0.3
        },
        'prompt': {
            'version': 'v1.0',
            'max_context': 4000
        }
    },
    'hybrid': {
        'retrieval': {
            'dense_weight': 0.7,
            'bm25_weight': 0.3,
            'top_k': 20
        }
    }
}
```

## Migration Path

1. **Week 1-2**: Extract current RAG logic → BaselineStrategy
2. **Week 3-4**: Validate equivalent results
3. **Week 5-6**: Implement HybridStrategy
4. **Week 7-8**: A/B test baseline vs hybrid
5. **Week 9-10**: Roll out winner to 100% traffic
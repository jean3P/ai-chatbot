# Prompt Templates

## Purpose
Prompt templates define how we construct LLM messages from retrieved context. They are versioned, tested, and treated as critical code.

## Why Version Prompts?

**Problem:** Changing prompts breaks reproducibility
```python
# What prompt version generated this answer?
# Can we reproduce it?
# How do we A/B test prompt changes?
```

**Solution:** Version control like code
```python
# Explicit version
prompt = load_template("system_prompt", version="v1.2")

# Track in metadata
answer.metadata = {
    "prompt_version": "v1.2",
    "llm_model": "gpt-4o-mini"
}
```

## Template Structure

```
prompts/
├── v1.0/                    # Initial version
│   ├── system_en.j2         # English system prompt
│   ├── system_de.j2         # German system prompt
│   └── user.j2              # User message template
├── v1.1/                    # Improved citations
│   ├── system_en.j2
│   ├── system_de.j2
│   └── user.j2
└── current -> v1.1          # Symlink to active version
```

## Template Example

**File:** `prompts/v1.0/system_en.j2`
```jinja2
You are a helpful AI assistant that answers questions based on provided documentation.

{% if context %}
CONTEXT FROM DOCUMENTATION:
{% for chunk in context %}
=== Document: {{ chunk.document_title }} (Page {{ chunk.page_number }}) ===
{{ chunk.content }}

{% endfor %}
{% endif %}

INSTRUCTIONS:
- Use the provided context to give accurate, specific answers
- ALWAYS cite sources using format: [Document Name, Page X]
- If context doesn't answer the question, say so clearly
- Provide step-by-step instructions when appropriate
- Keep responses clear and concise

{% if language != 'en' %}
Respond in {{ language_name }}.
{% endif %}
```

## Loading Templates

```python
from jinja2 import Environment, FileSystemLoader

class PromptTemplate:
    def __init__(self, version: str = "v1.0"):
        self.env = Environment(
            loader=FileSystemLoader(f"apps/domain/prompts/{version}"),
            autoescape=False  # Don't escape for LLM
        )
    
    def render_system(self, context: List[Chunk], language: str) -> str:
        template = self.env.get_template(f"system_{language}.j2")
        return template.render(
            context=context,
            language=language,
            language_name=self._language_name(language)
        )
```

## Version Strategy

### Semantic Versioning
- **v1.0** - Initial baseline
- **v1.1** - Minor improvements (better citations)
- **v2.0** - Major changes (different structure)

### When to Create New Version
- Citation format changes
- Instruction structure changes
- Adding/removing sections
- Language support changes

### When to Update Existing Version
- Typo fixes
- Clarification (not changing behavior)
- Variable name changes

## Testing Prompts

Prompts should have tests:

```python
def test_system_prompt_includes_context():
    template = PromptTemplate(version="v1.0")
    chunks = [
        Chunk(document_title="Manual", page_number=5, content="Install...")
    ]
    
    prompt = template.render_system(chunks, language="en")
    
    assert "CONTEXT FROM DOCUMENTATION" in prompt
    assert "Manual" in prompt
    assert "Page 5" in prompt

def test_system_prompt_german():
    template = PromptTemplate(version="v1.0")
    prompt = template.render_system([], language="de")
    
    assert "auf Deutsch" in prompt or "in German" in prompt
```

## Migration Strategy

### Deploying New Prompt Version

1. **Create new version folder**
   ```bash
   cp -r prompts/v1.0 prompts/v1.1
   # Edit templates
   ```

2. **Test in development**
   ```python
   config.PROMPT_VERSION = "v1.1"
   ```

3. **A/B test in production**
   ```python
   if experiment.variant == "A":
       version = "v1.0"  # Control
   else:
       version = "v1.1"  # Treatment
   ```

4. **Rollout gradually**
   - 10% traffic → v1.1
   - Monitor quality metrics
   - 50% traffic → v1.1
   - 100% traffic → v1.1

5. **Update default**
   ```bash
   ln -sf v1.1 prompts/current
   ```

## Multi-Language Support

Each version has language variants:

```
prompts/v1.0/
├── system_en.j2      # English
├── system_de.j2      # German
├── system_fr.j2      # French
└── system_es.j2      # Spanish
```

**Language selection:**
```python
template_name = f"system_{language}.j2"
template = env.get_template(template_name)
```

## Best Practices

### ✅ DO
- Version all prompts
- Test prompt changes
- Track version in metadata
- A/B test major changes
- Document reasoning for changes

### ❌ DON'T
- Modify existing versions (create new)
- Skip testing
- Deploy without A/B test
- Forget to update version config

## Prompt Engineering Checklist

When creating/updating prompts:
- [ ] Clear role definition
- [ ] Explicit instructions
- [ ] Example format (if needed)
- [ ] Citation requirements
- [ ] Error handling (no context case)
- [ ] Language specification
- [ ] Length constraints
- [ ] Tone/style guidance

## Configuration

Default version in `infrastructure/config.py`:

```python
PROMPT_CONFIG = {
    'default_version': 'v1.1',
    'fallback_version': 'v1.0',
    'template_dir': 'apps/domain/prompts'
}
```

## Metadata Tracking

Every answer records prompt version:

```python
answer.metadata = {
    'prompt_version': 'v1.1',
    'llm_model': 'gpt-4o-mini',
    'language': 'en',
    'method': 'baseline'
}
```

This enables:
- Reproducing answers
- Comparing prompt versions
- Debugging quality issues
- Analyzing performance by version
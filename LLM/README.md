# LLM Module

This package centralizes large-model calls for FinRegQA. It is designed so other modules can import stable helper functions instead of constructing model clients manually.

## Default Provider

The current default provider is Tongyi Qwen through DashScope's OpenAI-compatible endpoint.

- Default `base_url`: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Default `model`: `qwen-plus`

## Environment Variables

- `FINREGQA_LLM_PROVIDER`
- `FINREGQA_LLM_MODEL`
- `FINREGQA_LLM_API_KEY`
- `FINREGQA_LLM_BASE_URL`
- `FINREGQA_LLM_TEMPERATURE`
- `FINREGQA_LLM_MAX_TOKENS`
- `FINREGQA_LLM_TIMEOUT`
- `FINREGQA_LLM_MAX_RETRIES`
- `FINREGQA_LLM_ENABLE_THINKING`
- `FINREGQA_LLM_CACHE_ENABLED`
- `FINREGQA_LLM_USE_CACHE_ON_ERROR`
- `DASHSCOPE_API_KEY`

## Example

```python
from LLM import generate_rag_answer

refs = [
    {"document_name": "regulation_doc", "article_number": "article_3", "content": "..."},
]

result = generate_rag_answer("When should a report be submitted?", refs)
print(result.content)
```

## Streaming Example

```python
from LLM import stream_rag_answer

refs = [
    {"document_name": "regulation_doc", "article_number": "article_3", "content": "..."},
]

for chunk in stream_rag_answer("When should a report be submitted?", refs):
    print(chunk.channel, chunk.text, end="", flush=True)
```

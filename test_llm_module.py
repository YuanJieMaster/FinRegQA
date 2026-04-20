from LLM import load_llm_config
from LLM.prompts import build_context_block


def test_load_llm_config_defaults(monkeypatch):
    monkeypatch.delenv("FINREGQA_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("FINREGQA_LLM_MODEL", raising=False)
    monkeypatch.delenv("FINREGQA_LLM_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FINREGQA_LLM_BASE_URL", raising=False)

    config = load_llm_config()

    assert config.provider == "qwen"
    assert config.model == "qwen-plus"
    assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_build_context_block_contains_reference_metadata():
    refs = [
        {
            "document_name": "bank_rules",
            "article_number": "article_3",
            "section_number": "section_1",
            "similarity": 0.91,
            "content": "internal control is required",
        }
    ]

    text = build_context_block(refs)

    assert "参考材料1" in text
    assert "bank_rules" in text
    assert "article_3 section_1" in text
    assert "相似度: 0.910" in text
    assert "internal control is required" in text

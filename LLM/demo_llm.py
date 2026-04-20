"""Quick demo for the shared LLM module."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running via `python LLM/demo_llm.py` from the repo root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from LLM import load_llm_config, stream_rag_answer


def main() -> None:
    load_dotenv(".env")
    config = load_llm_config()

    print("=" * 80)
    print("FinRegQA LLM Demo")
    print("=" * 80)
    print(f"Provider: {config.provider}")
    print(f"Model: {config.model}")
    print(f"Base URL: {config.base_url}")
    print(f"API Key Loaded: {bool(config.api_key)}")
    print(f"Enable Thinking: {config.enable_thinking}")
    print("=" * 80)

    question = "商业银行资本充足率最低要求是什么？"
    references = [
        {
            "document_name": "商业银行资本管理办法",
            "article_number": "第二条",
            "section_number": "第一款",
            "similarity": 0.923,
            "content": (
                "银行资本充足率不得低于8%，其中核心一级资本充足率不得低于5%，"
                "一级资本充足率不得低于6%。"
            ),
        },
        {
            "document_name": "商业银行流动性风险管理规则",
            "article_number": "第三条",
            "section_number": "第一款",
            "similarity": 0.801,
            "content": "商业银行应当建立与其业务规模和复杂程度相适应的风险管理体系。",
        },
    ]

    print("Question:")
    print(question)
    print("\nReferences:")
    for idx, ref in enumerate(references, start=1):
        print(
            f"{idx}. {ref['document_name']} {ref['article_number']} {ref['section_number']} "
            f"(similarity={ref['similarity']})"
        )

    print("\nLLM Answer:\n")
    try:
        current_channel = None
        for chunk in stream_rag_answer(question, references):
            if chunk.channel != current_channel:
                current_channel = chunk.channel
                if current_channel == "reasoning":
                    print("[Thinking]")
                else:
                    print("\n[Answer]")
            print(chunk.text, end="", flush=True)
        print("\n")
        print("=" * 80)
        print(f"Model Used: {config.model}")
        print("=" * 80)
    except Exception as e:
        print("LLM call failed.")
        print(f"Error: {e}")
        print("\nPossible causes:")
        print("1. The current Qwen account free-tier quota has been exhausted.")
        print("2. Paid invocation is not enabled in DashScope console.")
        print("3. The API key does not have permission to call the selected model.")


if __name__ == "__main__":
    main()

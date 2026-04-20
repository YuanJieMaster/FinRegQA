"""
LLM 分块测试脚本
快速验证 LLM 智能分块功能是否正常工作

用法:
    python scripts/test_llm_chunking.py

依赖:
    - LLM 模块已配置 (见 .env 文件)
    - 需要 LLM API Key (如 DASHSCOPE_API_KEY 或 OPENAI_API_KEY)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_chunking import chunk_text_with_llm


SAMPLE_TEXT = """
中国银保监会关于加强商业银行监管的指导意见

第一条 为了加强商业银行监管，有效防范金融风险，保护存款人和其他客户的合法权益，促进银行业健康发展，根据相关法律法规，制定本办法。

第二条 本办法适用于在中华人民共和国境内设立的商业银行。

第三条 商业银行应当建立健全内部控制体系，确保业务稳健运行。

第四条 资本充足率不得低于百分之八。

第五条 流动性覆盖率应当不低于百分之一百。
"""


def test_llm_chunking():
    """测试 LLM 分块功能"""
    print("=" * 60)
    print("LLM 智能分块测试")
    print("=" * 60)

    try:
        result = chunk_text_with_llm(
            SAMPLE_TEXT,
            document_name="商业银行监管指导意见",
            category="银行监管",
            region="全国",
        )

        print(f"\n[OK] LLM 分块成功!")
        print(f"     分块数量: {result.total_chunks}")
        print(f"     总字符数: {result.total_chars}")

        if result.structure_summary:
            print(f"     结构概述: {result.structure_summary[:80]}...")

        print(f"\n各分块详情:")
        for i, chunk in enumerate(result.chunks):
            article = chunk.metadata.article_number or "无条款号"
            section = chunk.metadata.section_number or ""
            print(f"\n  块 {i + 1} (条款: {article} {section})")
            content = chunk.content[:80].replace("\n", " ")
            print(f"    内容: {content}...")

        return True

    except Exception as e:
        print(f"\n[FAIL] LLM 分块失败: {e}")
        print("     将使用规则分块作为回退")
        return False


def test_llm_chunking_with_custom_config():
    """测试使用自定义配置的 LLM 分块"""
    print("\n" + "=" * 60)
    print("自定义配置测试")
    print("=" * 60)

    try:
        from LLM import LLMConfig

        config = LLMConfig(
            provider="qwen",
            model="qwen-plus",
            temperature=0.1,
        )

        result = chunk_text_with_llm(
            SAMPLE_TEXT[:500],  # 使用较短文本
            document_name="测试文档",
            config=config,
        )

        print(f"\n[OK] 自定义配置测试成功!")
        print(f"     分块数量: {result.total_chunks}")

        return True

    except Exception as e:
        print(f"\n[FAIL] 自定义配置测试失败: {e}")
        return False


def test_rule_based_fallback():
    """测试规则分块回退"""
    print("\n" + "=" * 60)
    print("规则分块回退测试")
    print("=" * 60)

    try:
        from app.services.text_processor import TextSplitterService

        splitter = TextSplitterService(
            min_chunk_size=10,
            keep_separator=True,
        )

        chunks = splitter.split_text(SAMPLE_TEXT)

        print(f"\n[OK] 规则分块成功!")
        print(f"     分块数量: {len(chunks)}")

        for i, chunk in enumerate(chunks[:3]):
            content = chunk[:60].replace("\n", " ")
            print(f"     块 {i + 1}: {content}...")

        return True

    except Exception as e:
        print(f"\n[FAIL] 规则分块失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("FinRegQA LLM 分块测试套件")
    print("=" * 60)
    print("\n注意: 确保已配置 LLM API Key")
    print("      (DASHSCOPE_API_KEY 或 OPENAI_API_KEY)\n")

    results = []

    # 测试 1: LLM 分块
    results.append(("LLM 分块", test_llm_chunking()))

    # 测试 2: 自定义配置
    results.append(("自定义配置", test_llm_chunking_with_custom_config()))

    # 测试 3: 规则分块回退
    results.append(("规则分块", test_rule_based_fallback()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n所有测试通过!")
    else:
        print("\n部分测试失败，请检查配置。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

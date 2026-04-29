"""
AI问答对生成功能快速测试脚本
自动执行所有测试，无需交互
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.qa_generator import (
    QAGenerator,
    UNIVERSAL_QA_TEMPLATES,
)


def main():
    print("=" * 60)
    print("AI问答对生成功能测试")
    print("=" * 60)

    # 测试1: 初始化
    print("\n[1/4] 测试生成器初始化...")
    try:
        generator = QAGenerator()
        print(f"      [OK] 初始化成功")
        print(f"           LLM: {generator.llm_config.model}")
    except Exception as e:
        print(f"      [FAIL] {e}")
        return

    # 测试2: 模板
    print(f"\n[2/4] 验证通用模板 ({len(UNIVERSAL_QA_TEMPLATES)} 个)...")
    by_diff = {}
    for t in UNIVERSAL_QA_TEMPLATES:
        by_diff[t.difficulty] = by_diff.get(t.difficulty, 0) + 1
    print(f"      [OK] 难度分布: {by_diff}")

    # 测试3: 生成通用问答对
    print(f"\n[3/4] 调用AI生成5个通用问答对...")
    try:
        result = generator.generate_universal(count=5)
        if result:
            print(f"      [OK] 生成成功!")
            print(f"           数量: {len(result)}")
            for i, qa in enumerate(result[:2], 1):
                print(f"           [{i}] {qa.question[:40]}...")
        else:
            print(f"      [WARN] 返回空结果")
    except Exception as e:
        print(f"      [FAIL] {e}")

    # 测试4: 生成文档问答对
    print(f"\n[4/4] 测试文档问答对生成...")
    sample_doc = """
    商业银行风险管理指引

    第一条 为了加强商业银行风险管理，保障商业银行安全稳健运行，根据相关法律法规，制定本指引。

    第二条 风险管理应当覆盖信用风险、市场风险、操作风险、流动性风险等各类风险。

    第三条 商业银行资本充足率不得低于8%，核心资本充足率不得低于4%。
    """
    try:
        result = generator.generate_for_document(
            document_content=sample_doc,
            document_name="测试文档",
            count=3
        )
        if result:
            print(f"      [OK] 生成成功!")
            print(f"           数量: {len(result)}")
        else:
            print(f"      [WARN] 返回空结果")
    except Exception as e:
        print(f"      [FAIL] {e}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print("\n查看生成结果:")
    print("  目录: data/evaluation/qa_generation/pending_review/")
    print("  运行 generator.load_pending_review() 查看待核验问答对")
    print("\nAPI端点:")
    print("  POST /api/qa-generation/generate/universal")
    print("  POST /api/qa-generation/generate/document")
    print("  GET  /api/qa-generation/pending")
    print("  POST /api/qa-generation/review")


if __name__ == "__main__":
    main()

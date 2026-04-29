"""
AI问答对生成功能测试脚本
用于测试问答对生成服务
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.qa_generator import (
    QAGenerator,
    get_qa_generator,
    UNIVERSAL_QA_TEMPLATES,
)


def test_generator_initialization():
    """测试生成器初始化"""
    print("=" * 60)
    print("测试1: 问答对生成器初始化")
    print("=" * 60)

    try:
        generator = QAGenerator()
        print(f"[OK] 生成器初始化成功")
        print(f"     LLM配置: {generator.llm_config.model} @ {generator.llm_config.base_url}")
        return True
    except Exception as e:
        print(f"[FAIL] 初始化失败: {e}")
        return False


def test_universal_templates():
    """测试通用模板"""
    print("\n" + "=" * 60)
    print("测试2: 通用问答模板")
    print("=" * 60)

    print(f"\n共有 {len(UNIVERSAL_QA_TEMPLATES)} 个通用模板:\n")

    # 按难度分类统计
    by_difficulty = {"easy": [], "medium": [], "hard": []}
    by_type = {}

    for t in UNIVERSAL_QA_TEMPLATES:
        by_difficulty[t.difficulty].append(t.template)
        qtype = t.question_type
        if qtype not in by_type:
            by_type[qtype] = []
        by_type[qtype].append(t.template)

    print("按难度分布:")
    for diff, templates in by_difficulty.items():
        print(f"  {diff}: {len(templates)} 个")

    print("\n按类型分布:")
    for qtype, templates in by_type.items():
        print(f"  {qtype}: {len(templates)} 个")

    print("\n模板示例:")
    for i, t in enumerate(UNIVERSAL_QA_TEMPLATES[:3], 1):
        print(f"\n  {i}. [{t.difficulty}] {t.question_type}")
        print(f"     问题: {t.template[:50]}...")
        print(f"     答案要点: {t.answer_guidance[:50]}...")

    return True


def test_statistics():
    """测试统计功能"""
    print("\n" + "=" * 60)
    print("测试3: 统计信息")
    print("=" * 60)

    generator = get_qa_generator()
    stats = generator.get_statistics()

    print("\n问答对统计:")
    print(f"  待核验: {stats['pending_review']} 个")
    print(f"  已批准: {stats['approved']} 个")
    print(f"  总计: {stats['total']} 个")

    print("\n已批准问答对分布:")
    print(f"  按难度: {stats['difficulty_distribution']}")
    print(f"  按类型: {stats['type_distribution']}")

    return True


def test_generate_universal():
    """测试生成通用问答对（需要API调用）"""
    print("\n" + "=" * 60)
    print("测试4: 生成通用问答对（实际API调用）")
    print("=" * 60)

    generator = get_qa_generator()

    print("\n正在调用AI生成问答对，请稍候...")

    try:
        result = generator.generate_universal(count=5)

        if result.get("success"):
            print(f"\n[OK] 生成成功!")
            print(f"     生成数量: {result.get('total_generated', 0)}")
            print(f"     保存路径: {result.get('pending_review_file', '')}")

            qa_pairs = result.get("qa_pairs", [])
            print(f"\n生成的问答对预览:")
            for i, qa in enumerate(qa_pairs[:3], 1):
                print(f"\n  问答对 {i}:")
                print(f"    问题: {qa['question'][:60]}...")
                print(f"    答案: {qa['ground_truth_answer'][:60]}...")
                print(f"    难度: {qa['difficulty']} | 类型: {qa['question_type']}")
                print(f"    关键词: {', '.join(qa['keywords'][:3])}")
                print(f"    AI置信度: {qa['ai_confidence']:.2f}")

            return True
        else:
            print(f"\n[FAIL] 生成失败: {result.get('error', '未知错误')}")
            return False

    except Exception as e:
        print(f"\n[FAIL] API调用失败: {e}")
        print("     这可能是网络问题或API配置错误")
        return False


def test_document_qa_generation():
    """测试文档问答对生成"""
    print("\n" + "=" * 60)
    print("测试5: 文档问答对生成")
    print("=" * 60)

    sample_document = """商业银行风险管理指引

第一章 总则
第一条 为了加强商业银行风险管理，保障商业银行安全稳健运行，根据《中华人民共和国银行业监督管理法》等法律法规，制定本指引。

第二条 本指引所称风险管理，是指商业银行通过识别、计量、监测、控制等方式，对各类风险进行有效管理的过程。

第三条 商业银行应当建立健全风险管理体系，明确风险管理组织架构、职责分工和报告路线。

第二章 风险管理框架
第四条 商业银行应当建立完善的风险管理治理架构，包括董事会、监事会、高级管理层和风险管理职能部门。

第五条 风险管理应当覆盖信用风险、市场风险、操作风险、流动性风险、法律风险、声誉风险等各类风险。

第六条 商业银行应当制定风险管理政策和程序，明确风险偏好、风险限额和风险控制措施。

第三章 资本管理
第七条 商业银行资本充足率不得低于8%，核心资本充足率不得低于4%。

第八条 商业银行应当加强资本管理，确保资本充足率持续符合监管要求。

第九条 商业银行应当建立资本规划机制，合理配置经济资本。
"""

    generator = get_qa_generator()

    print("\n正在分析文档并生成问答对...")

    try:
        result = generator.generate_for_document(
            document_content=sample_document,
            document_name="商业银行风险管理指引（测试）",
            count=5
        )

        if result:
            print(f"\n[OK] 生成成功!")
            print(f"     生成数量: {len(result)}")

            print(f"\n生成的问答对预览:")
            for i, qa in enumerate(result[:3], 1):
                print(f"\n  问答对 {i}:")
                print(f"    问题: {qa.question[:60]}...")
                print(f"    答案: {qa.ground_truth_answer[:60]}...")
                print(f"    难度: {qa.difficulty} | 类型: {qa.question_type}")

            return True
        else:
            print(f"\n[FAIL] 生成失败")
            return False

    except Exception as e:
        print(f"\n[FAIL] 生成失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("AI问答对生成功能测试")
    print("=" * 60)

    results = []

    # 测试1: 初始化
    results.append(("初始化", test_generator_initialization()))

    # 测试2: 模板
    results.append(("通用模板", test_universal_templates()))

    # 测试3: 统计
    results.append(("统计功能", test_statistics()))

    # 测试4: 生成通用问答对（需要实际API调用）
    print("\n" + "-" * 60)
    print("提示: 接下来的测试将实际调用AI API，可能需要一些时间")
    print("-" * 60)

    response = input("\n是否执行API调用测试? (y/n): ").strip().lower()
    if response == 'y':
        results.append(("生成通用问答对", test_generate_universal()))
        results.append(("文档问答对生成", test_document_qa_generation()))
    else:
        print("\n[跳过] API调用测试")

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n通过: {passed_count}/{len(results)}")

    if passed_count == len(results):
        print("\n所有测试通过!")
    else:
        print("\n部分测试失败，请检查配置。")


if __name__ == "__main__":
    main()

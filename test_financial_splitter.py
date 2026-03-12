"""
金融制度文本分块器测试代码
Test Script for Financial Regulation Text Splitter

功能：
1. 测试文档加载功能（PDF/DOCX/TXT）
2. 测试自定义分块器效果
3. 输出分块统计信息
"""

from financial_text_splitter import (
    FinancialRegulationSplitter,
    load_financial_document,
    clean_financial_text
)
from langchain_core.documents import Document


def test_with_sample_text():
    """
    使用示例文本测试分块器
    
    模拟真实的金融监管文件结构
    """
    print("=" * 80)
    print("测试1：使用示例金融监管文本")
    print("=" * 80)
    
    # 模拟金融监管文件内容（包含章、条、款、项结构）
    sample_text = """
    第一章 总则
    
    第一条 为规范金融机构的经营行为，防范金融风险，保护投资者合法权益，根据《中华人民共和国银行业监督管理法》等法律法规，制定本办法。本办法适用于在中华人民共和国境内依法设立的商业银行、信托公司、证券公司等金融机构。
    
    第二条 金融机构应当遵循诚实信用、勤勉尽责的原则，建立健全内部控制制度，有效识别、计量、监测和控制各类风险。金融机构应当加强风险管理，确保业务发展与风险管理能力相匹配。
    
    第二章 风险管理
    
    第三条 金融机构应当建立全面风险管理体系，包括但不限于以下内容：（一）信用风险管理。金融机构应当建立完善的信用风险识别、评估、监测和控制机制，对借款人的信用状况进行持续跟踪；（二）市场风险管理。金融机构应当建立市场风险限额管理制度，定期进行压力测试和情景分析；（三）操作风险管理。金融机构应当识别业务流程中的操作风险点，建立有效的内部控制措施。
    
    第四条 金融机构应当按照监管要求，定期向监管部门报送风险管理报告。报告内容应当真实、准确、完整，不得隐瞒或虚报重大风险信息。对于重大风险事件，应当在发现后24小时内向监管部门报告。
    
    第三章 资本管理
    
    第五条 金融机构应当保持充足的资本水平，资本充足率不得低于监管要求的最低标准。商业银行的核心一级资本充足率不得低于5%，一级资本充足率不得低于6%，资本充足率不得低于8%。
    
    第六条 金融机构应当制定资本规划，确保资本水平与业务发展、风险状况相适应。资本规划应当包括资本目标、资本补充计划、资本分配策略等内容。
    
    第四章 附则
    
    第七条 本办法由中国银行保险监督管理委员会负责解释。
    
    第八条 本办法自2024年1月1日起施行。
    
    内部资料 第1页 2024-01-01
    """
    
    # 初始化分块器
    splitter = FinancialRegulationSplitter(
        min_chunk_size=0,  # 不过滤短片段
        keep_separator=True
    )
    
    # 清洗文本
    cleaned_text = clean_financial_text(sample_text)
    print(f"\n原始文本长度: {len(sample_text)} 字符")
    print(f"清洗后文本长度: {len(cleaned_text)} 字符")
    print(f"清洗效果: 去除了 {len(sample_text) - len(cleaned_text)} 个字符（水印、页码等）")
    
    # 分块
    chunks = splitter.split_text(cleaned_text)
    
    print(f"\n分块结果统计:")
    print(f"- 知识点数量: {len(chunks)} 个")
    print(f"- 平均长度: {sum(len(c) for c in chunks) / len(chunks):.0f} 字符")
    print(f"- 最短片段: {min(len(c) for c in chunks)} 字符")
    print(f"- 最长片段: {max(len(c) for c in chunks)} 字符")
    
    print(f"\n分块详情:")
    for i, chunk in enumerate(chunks, 1):
        # 提取chunk的前50个字符作为预览
        preview = chunk[:50].replace("\n", " ")
        print(f"  [{i}] 长度={len(chunk):4d}字 | 预览: {preview}...")
    
    print("\n完整分块内容展示（前3个）:")
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"\n--- Chunk {i} ---")
        print(chunk)
        print(f"--- 长度: {len(chunk)} 字符 ---")


def test_with_real_document(file_path: str):
    """
    测试真实文档加载和分块
    
    Args:
        file_path: 文档路径（PDF/DOCX/TXT）
    """
    print("\n" + "=" * 80)
    print(f"测试2：加载真实文档 - {file_path}")
    print("=" * 80)
    
    try:
        # 加载文档
        print("\n正在加载文档...")
        document = load_financial_document(file_path, clean_text=True)
        
        print(f"✓ 文档加载成功")
        print(f"  - 文件名: {document.metadata['file_name']}")
        print(f"  - 文件类型: {document.metadata['file_type']}")
        print(f"  - 文本长度: {len(document.page_content)} 字符")
        
        # 分块
        print("\n正在进行智能分块...")
        splitter = FinancialRegulationSplitter(
            min_chunk_size=0,  # 不过滤短片段
            keep_separator=True
        )
        
        chunks = splitter.split_text(document.page_content)
        
        print(f"✓ 分块完成")
        print(f"\n📊 分块统计:")
        print(f"  - 知识点总数: {len(chunks)} 个")
        print(f"  - 平均长度: {sum(len(c) for c in chunks) / len(chunks):.0f} 字符")
        print(f"  - 最短片段: {min(len(c) for c in chunks)} 字符")
        print(f"  - 最长片段: {max(len(c) for c in chunks)} 字符")
        
        # 长度分布统计
        length_ranges = {
            "50字以下": 0,
            "50-200字": 0,
            "200-500字": 0,
            "500-1000字": 0,
            "1000-2000字": 0,
            "2000字以上": 0
        }
        
        for chunk in chunks:
            length = len(chunk)
            if length < 50:
                length_ranges["50字以下"] += 1
            elif length < 200:
                length_ranges["50-200字"] += 1
            elif length < 500:
                length_ranges["200-500字"] += 1
            elif length < 1000:
                length_ranges["500-1000字"] += 1
            elif length < 2000:
                length_ranges["1000-2000字"] += 1
            else:
                length_ranges["2000字以上"] += 1
        
        print(f"\n📈 长度分布:")
        for range_name, count in length_ranges.items():
            percentage = (count / len(chunks)) * 100
            print(f"  - {range_name}: {count} 个 ({percentage:.1f}%)")
        
        # 展示前5个分块的预览
        print(f"\n📄 分块预览（前5个）:")
        for i, chunk in enumerate(chunks[:5], 1):
            preview = chunk[:80].replace("\n", " ")
            print(f"  [{i}] {preview}...")
        
        # 检测章节结构
        chapter_count = sum(1 for c in chunks if "第" in c[:10] and "章" in c[:10])
        article_count = sum(1 for c in chunks if "第" in c[:10] and "条" in c[:10])
        
        print(f"\n🏗️  文档结构分析:")
        print(f"  - 检测到章节: {chapter_count} 个")
        print(f"  - 检测到条款: {article_count} 个")
        
        return chunks
        
    except FileNotFoundError:
        print(f"❌ 错误: 文件不存在 - {file_path}")
        print(f"   请确保文件路径正确，或使用示例文本测试")
    except Exception as e:
        print(f"❌ 错误: {str(e)}")


def create_sample_txt_file():
    """
    创建示例TXT文件用于测试
    """
    sample_content = """第一章 总则

第一条 为加强金融机构流动性风险管理，提高金融机构稳健性，根据《中华人民共和国银行业监督管理法》《中华人民共和国商业银行法》等法律法规，制定本办法。

第二条 本办法适用于中华人民共和国境内依法设立的商业银行、农村合作银行、农村信用合作社等吸收公众存款的金融机构，以及政策性银行。

第三条 本办法所称流动性风险，是指商业银行无法以合理成本及时获得充足资金，用于偿付到期债务、履行其他支付义务和满足正常业务开展的其他资金需求的风险。

第二章 流动性风险管理

第四条 商业银行应当建立健全流动性风险管理体系，确保流动性风险管理覆盖所有业务、产品和地域。流动性风险管理体系应当包括以下内容：（一）完善的公司治理结构；（二）有效的流动性风险管理政策和程序；（三）准确的流动性风险识别、计量、监测和控制；（四）完备的管理信息系统。

第五条 商业银行应当制定流动性风险管理策略，明确流动性风险偏好、管理目标和实施路径。流动性风险管理策略应当与商业银行的业务性质、规模、复杂程度和风险特征相适应。

第六条 商业银行应当建立流动性风险限额管理制度，设定流动性风险限额指标，并定期评估和调整。流动性风险限额应当覆盖表内外业务，包括但不限于流动性覆盖率、净稳定资金比例等监管指标。

第三章 流动性风险监测

第七条 商业银行应当建立流动性风险监测机制，持续监测流动性状况和流动性风险水平。监测内容应当包括：（一）现金流分析；（二）流动性缺口分析；（三）流动性集中度分析；（四）流动性压力测试。

第八条 商业银行应当定期开展流动性压力测试，评估在压力情景下的流动性状况。压力测试应当至少包括轻度、中度和重度三种压力情景，并考虑市场流动性风险和融资流动性风险的相互影响。

第四章 监督管理

第九条 银行业监督管理机构依法对商业银行流动性风险管理实施监督检查。商业银行应当按照监管要求，定期报送流动性风险管理报告和相关数据。

第十条 商业银行流动性覆盖率应当不低于100%。流动性覆盖率是指优质流动性资产储备与未来30日的资金净流出量之比。

第十一条 商业银行净稳定资金比例应当不低于100%。净稳定资金比例是指可用的稳定资金与所需的稳定资金之比。

第五章 附则

第十二条 本办法由中国银行保险监督管理委员会负责解释。

第十三条 本办法自发布之日起施行。"""
    
    file_path = "d:\\Github\\FinRegQA\\sample_financial_regulation.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(sample_content)
    
    print(f"✓ 已创建示例文件: {file_path}")
    return file_path


def main():
    """
    主测试函数
    """
    print("\n" + "=" * 80)
    print("金融制度文本分块器 - 测试程序")
    print("Financial Regulation Text Splitter - Test Suite")
    print("=" * 80)
    
    # 测试1：使用内置示例文本
    test_with_sample_text()
    
    # 测试2：创建并测试TXT文件
    print("\n")
    sample_file = create_sample_txt_file()
    test_with_real_document(sample_file)
    
    # 测试3：如果有真实的PDF文件，可以测试
    # print("\n" + "=" * 80)
    # print("提示：如果您有金融监管PDF文件，可以使用以下代码测试：")
    # print("=" * 80)

    # from financial_text_splitter import FinancialRegulationSplitter, load_financial_document

    # # 加载PDF文档
    # document = load_financial_document("your_pdf_file.pdf", clean_text=True)

    # # 分块（不过滤短片段）
    # splitter = FinancialRegulationSplitter(min_chunk_size=0)
    # chunks = splitter.split_text(document.page_content)

    # print(f"知识点数量: {len(chunks)}")
    # for chunk in chunks:
    #     print(chunk)
    #     print("-" * 80)

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()

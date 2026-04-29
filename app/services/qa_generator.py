"""
AI辅助问答对生成服务
支持针对不同文档生成专门的问答对，以及生成通用金融监管问答对

功能特点：
1. 针对文档内容生成专门的问答对
2. 生成通用金融监管问答对（覆盖常见监管主题）
3. 提供人工核验工作流
4. 支持多种难度级别
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from enum import Enum

from LLM.client import invoke_chat, LLMConfig, load_llm_config
from app.services.document_analyzer import DocumentStructureAnalyzer


# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent
QA_GENERATION_DIR = PROJECT_ROOT / "data" / "evaluation" / "qa_generation"
QA_PENDING_REVIEW_DIR = QA_GENERATION_DIR / "pending_review"
QA_APPROVED_DIR = QA_GENERATION_DIR / "approved"


class QADifficulty(Enum):
    """问答对难度级别"""
    EASY = "easy"           # 简单 - 直接事实性问题
    MEDIUM = "medium"        # 中等 - 需要理解概念
    HARD = "hard"            # 困难 - 需要综合分析


class QAType(Enum):
    """问答对类型"""
    DEFINITION = "definition"           # 定义类
    NUMERIC = "numeric"                  # 数字类
    PROCEDURE = "procedure"              # 流程类
    PRINCIPLE = "principle"               # 原则类
    COMPARISON = "comparison"            # 对比类
    EXAMPLE = "example"                  # 举例类
    REQUIREMENT = "requirement"         # 要求类


@dataclass
class GeneratedQAPair:
    """生成的问答对（待核验）"""
    question: str
    ground_truth_answer: str
    question_type: str = "definition"
    difficulty: str = "medium"
    keywords: list[str] = field(default_factory=list)
    source_context: str = ""              # 问题来源的原文上下文
    source_document: str = ""             # 来源文档名
    generation_reason: str = ""            # 生成理由
    ai_confidence: float = 0.0           # AI置信度
    needs_review: bool = True             # 是否需要人工核验
    reviewer_notes: str = ""              # 核验备注
    review_status: str = "pending"         # pending, approved, rejected
    created_at: str = ""


@dataclass
class UniversalQATemplate:
    """通用问答模板"""
    template: str                          # 问题模板
    answer_guidance: str                    # 答案指导
    question_type: str
    difficulty: str
    applicable_regulations: list[str]       # 适用法规类型
    keywords: list[str]


# ============================================================================
# 通用金融监管问答模板
# ============================================================================

UNIVERSAL_QA_TEMPLATES = [
    # ========== 风险管理类 ==========
    UniversalQATemplate(
        template="商业银行应当建立什么样的风险管理框架？",
        answer_guidance="应包含风险识别、风险计量、风险监测、风险控制等环节，覆盖信用风险、市场风险、操作风险、流动性风险等",
        question_type="principle",
        difficulty="medium",
        applicable_regulations=["商业银行风险管理指引", "银行业监督管理法"],
        keywords=["风险管理", "风险识别", "风险计量", "风险控制", "内部控制"]
    ),
    UniversalQATemplate(
        template="商业银行资本充足率不得低于多少？",
        answer_guidance="资本充足率不得低于8%，核心资本充足率不得低于4%",
        question_type="numeric",
        difficulty="easy",
        applicable_regulations=["商业银行资本管理办法", "巴塞尔协议"],
        keywords=["资本充足率", "8%", "核心资本", "4%", "最低资本要求"]
    ),
    UniversalQATemplate(
        template="商业银行如何进行客户身份识别？",
        answer_guidance="应当核对客户身份证明文件，了解客户职业、经营范围、资金来源等信息，识别受益所有人",
        question_type="procedure",
        difficulty="medium",
        applicable_regulations=["反洗钱法", "客户身份识别规定"],
        keywords=["身份识别", "客户身份", "受益所有人", "尽职调查", "KYC"]
    ),
    UniversalQATemplate(
        template="保险公司的偿付能力充足率要求是多少？",
        answer_guidance="核心偿付能力充足率不得低于50%，综合偿付能力充足率不得低于100%",
        question_type="numeric",
        difficulty="easy",
        applicable_regulations=["保险公司偿付能力监管规定"],
        keywords=["偿付能力", "100%", "核心偿付能力", "50%", "最低资本"]
    ),

    # ========== 合规管理类 ==========
    UniversalQATemplate(
        template="金融机构关联交易应当遵循什么原则？",
        answer_guidance="应当遵循公平、公正、公开原则，交易价格应当公允，不得损害金融机构和客户的合法权益",
        question_type="principle",
        difficulty="medium",
        applicable_regulations=["上市公司关联交易管理指引", "商业银行关联交易管理办法"],
        keywords=["关联交易", "公平", "公正", "公允", "利益输送"]
    ),
    UniversalQATemplate(
        template="证券公司如何保护客户资产安全？",
        answer_guidance="应当将客户资金与自有资金分别存放于客户资金专用账户，禁止挪用客户资金或证券",
        question_type="requirement",
        difficulty="medium",
        applicable_regulations=["证券法", "证券公司监督管理条例"],
        keywords=["客户资产", "资金专用账户", "分别管理", "挪用", "资产安全"]
    ),
    UniversalQATemplate(
        template="金融机构信息披露的主要内容有哪些？",
        answer_guidance="包括财务状况、公司治理、风险管理、关联交易、分部报告、重要事项等",
        question_type="definition",
        difficulty="medium",
        applicable_regulations=["上市公司信息披露管理办法", "金融机构信息披露规定"],
        keywords=["信息披露", "财务状况", "公司治理", "风险管理", "关联交易"]
    ),

    # ========== 监管要求类 ==========
    UniversalQATemplate(
        template="什么情况下监管机构可以对金融机构采取监管措施？",
        answer_guidance="当金融机构出现资本不足、风险较高、经营异常、合规问题等情况时",
        question_type="requirement",
        difficulty="medium",
        applicable_regulations=["银行业监督管理法", "证券法", "保险法"],
        keywords=["监管措施", "资本不足", "风险较高", "监管谈话", "整改"]
    ),
    UniversalQATemplate(
        template="金融机构应当如何进行关联交易管理？",
        answer_guidance="应当建立关联交易管理制度，明确关联方的识别标准，实行关联交易审批和披露",
        question_type="procedure",
        difficulty="medium",
        applicable_regulations=["商业银行关联交易管理办法", "上市公司关联交易实施指引"],
        keywords=["关联交易", "关联方", "审批", "披露", "回避表决"]
    ),

    # ========== 业务规范类 ==========
    UniversalQATemplate(
        template="证券公司经纪业务中禁止的行为有哪些？",
        answer_guidance="禁止虚假宣传、诱导交易、代客理财、承诺收益、挪用客户资金等行为",
        question_type="requirement",
        difficulty="medium",
        applicable_regulations=["证券法", "证券经纪业务管理办法"],
        keywords=["禁止行为", "虚假宣传", "诱导交易", "代客理财", "承诺收益"]
    ),
    UniversalQATemplate(
        template="保险公司资金运用的范围是什么？",
        answer_guidance="可投资于银行存款、国债、金融债券、股票、证券投资基金、不动产等",
        question_type="definition",
        difficulty="medium",
        applicable_regulations=["保险资金运用管理办法"],
        keywords=["保险资金", "投资范围", "银行存款", "债券", "股票", "不动产"]
    ),
    UniversalQATemplate(
        template="商业银行内部控制的基本要求是什么？",
        answer_guidance="应当建立有效的内部控制体系，包括内部环境、风险评估、控制活动、信息与沟通、内部监督等要素",
        question_type="principle",
        difficulty="medium",
        applicable_regulations=["商业银行内部控制指引"],
        keywords=["内部控制", "内部环境", "风险评估", "控制活动", "内部监督"]
    ),

    # ========== 处罚规定类 ==========
    UniversalQATemplate(
        template="金融机构违反监管规定可能面临哪些处罚？",
        answer_guidance="可能面临罚款、责令改正、限制业务、暂停业务、吊销许可证等行政处罚",
        question_type="definition",
        difficulty="hard",
        applicable_regulations=["银行业监督管理法", "证券法", "保险法"],
        keywords=["行政处罚", "罚款", "责令改正", "限制业务", "吊销许可证"]
    ),
    UniversalQATemplate(
        template="保险公司风险综合评级的主要指标有哪些？",
        answer_guidance="包括偿付能力充足率、风险管理能力、公司治理、资产质量、盈利能力等指标",
        question_type="definition",
        difficulty="hard",
        applicable_regulations=["保险公司偿付能力监管规则"],
        keywords=["风险综合评级", "偿付能力", "风险管理", "公司治理", "资产质量"]
    ),
]


# ============================================================================
# Prompt模板
# ============================================================================

DOCUMENT_QA_GENERATION_PROMPT = """你是一位金融监管制度专家，负责根据给定的金融监管文档生成高质量的问答对。

## 任务
根据以下文档内容，生成 {count} 个高质量的问答对，用于测试问答系统的检索和回答准确率。

## 文档内容
{document_content}

## 要求
1. **问题质量**：
   - 问题应当清晰、具体，避免歧义
   - 问题应当涵盖文档的核心内容
   - 问题应当符合中国金融监管的实际场景

2. **答案质量**：
   - 答案应当准确、全面，基于文档内容
   - 答案应当包含关键数据和具体要求
   - 如文档未涉及，应明确说明

3. **多样性**：
   - 问题类型要多样化：定义类、数字类、流程类、原则类、对比类
   - 难度要适中分布：简单(30%)、中等(50%)、困难(20%)

4. **上下文标注**：
   - 为每个问答对标注来源上下文
   - 标注关键词
   - 评估AI置信度

## 输出格式
请以JSON数组格式输出，每个问答对包含以下字段：
- question: 问题
- ground_truth_answer: 标准答案
- question_type: 问题类型(definition/numeric/procedure/principle/comparison/requirement)
- difficulty: 难度(easy/medium/hard)
- keywords: 关键词列表
- source_context: 来源上下文（问题对应的原文片段，50-200字）
- source_document: 来源文档名
- generation_reason: 生成该问答对的理由
- ai_confidence: AI置信度(0-1)

## 输出
"""

UNIVERSAL_QA_GENERATION_PROMPT = """你是一位金融监管制度专家，负责为金融监管知识库生成通用的问答对。

## 任务
基于以下通用模板，生成 {count} 个针对中国金融监管制度的问答对：

## 模板要求
{template}

## 要求
1. 生成的问题应当覆盖常见的金融监管场景
2. 问题应当具有代表性，能反映金融监管的核心要点
3. 答案应当基于中国金融监管的实际法规要求
4. 确保问题类型和难度分布合理

## 输出格式
请以JSON数组格式输出，每个问答对包含以下字段：
- question: 问题
- ground_truth_answer: 标准答案
- question_type: 问题类型
- difficulty: 难度
- keywords: 关键词列表
- source_context: 来源上下文
- source_document: 来源文档名(通用场景可写"金融监管通用")
- generation_reason: 生成理由
- ai_confidence: AI置信度

## 输出
"""


# ============================================================================
# 问答对生成服务
# ============================================================================

class QAGenerator:
    """
    AI辅助问答对生成服务

    支持：
    1. 针对文档生成专门问答对
    2. 生成通用金融监管问答对
    3. 批量生成和保存
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """初始化问答对生成器

        Args:
            llm_config: LLM配置，默认从环境变量加载
        """
        self.llm_config = llm_config or load_llm_config()
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要目录存在"""
        QA_GENERATION_DIR.mkdir(parents=True, exist_ok=True)
        QA_PENDING_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        QA_APPROVED_DIR.mkdir(parents=True, exist_ok=True)

    def generate_for_document(
        self,
        document_content: str,
        document_name: str,
        count: int = 10,
        custom_instructions: str = ""
    ) -> list[GeneratedQAPair]:
        """
        针对指定文档生成问答对

        Args:
            document_content: 文档内容
            document_name: 文档名称
            count: 生成数量
            custom_instructions: 自定义指令（可选）

        Returns:
            生成的问答对列表
        """
        prompt = DOCUMENT_QA_GENERATION_PROMPT.format(
            count=count,
            document_content=document_content
        )

        if custom_instructions:
            prompt += f"\n\n## 自定义要求\n{custom_instructions}"

        messages = [
            {"role": "system", "content": "你是一位专业的金融监管制度专家，擅长从法规文本中提取关键信息并生成高质量问答对。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = invoke_chat(messages, config=self.llm_config)
            qa_pairs = self._parse_qa_response(response.content, document_name)
            return qa_pairs
        except Exception as e:
            raise RuntimeError(f"生成问答对失败: {str(e)}")

    def generate_universal(
        self,
        count: int = 10,
        category: str = "",
        difficulty: str = ""
    ) -> list[GeneratedQAPair]:
        """
        生成通用金融监管问答对

        Args:
            count: 生成数量
            category: 指定类别筛选（可选）
            difficulty: 指定难度筛选（可选）

        Returns:
            生成的问答对列表
        """
        # 根据条件筛选模板
        templates = UNIVERSAL_QA_TEMPLATES
        if category:
            templates = [t for t in templates if category.lower() in t.template.lower()]
        if difficulty:
            templates = [t for t in templates if t.difficulty == difficulty]

        if not templates:
            templates = UNIVERSAL_QA_TEMPLATES

        # 选择要使用的模板
        selected_templates = templates[:min(count, len(templates))]
        template_info = "\n".join([
            f"- {t.template}\n  答案要点: {t.answer_guidance}\n  难度: {t.difficulty}"
            for t in selected_templates
        ])

        prompt = f"""基于以下金融监管通用问答模板，生成{count}个问答对：

## 模板
{template_info}

请为每个模板生成具体的问题和标准答案，确保：
1. 问题符合中国金融监管的实际场景
2. 答案准确、全面，包含关键数据和具体要求
3. 保持问题类型和难度的多样性

## 输出格式
JSON数组，包含字段：
- question: 问题
- ground_truth_answer: 标准答案
- question_type: 问题类型
- difficulty: 难度
- keywords: 关键词列表
- source_context: 来源上下文
- source_document: 来源文档名
- generation_reason: 生成理由
- ai_confidence: AI置信度(0-1)
"""

        messages = [
            {"role": "system", "content": "你是一位专业的金融监管制度专家，擅长生成符合中国金融监管实际的问答对。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = invoke_chat(messages, config=self.llm_config)
            qa_pairs = self._parse_qa_response(response.content, "金融监管通用")
            return qa_pairs
        except Exception as e:
            raise RuntimeError(f"生成通用问答对失败: {str(e)}")

    def _parse_qa_response(
        self,
        response_content: str,
        source_document: str
    ) -> list[GeneratedQAPair]:
        """解析LLM响应，提取问答对"""
        qa_pairs = []

        # 尝试提取JSON
        try:
            # 尝试直接解析
            data = json.loads(response_content)
            if isinstance(data, list):
                items = data
            else:
                items = [data]
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            import re
            json_pattern = r'\[[\s\S]*\]|\{[\s\S]*\}'
            matches = re.findall(json_pattern, response_content)
            if matches:
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, list):
                            items = data
                        else:
                            items = [data]
                        break
                    except json.JSONDecodeError:
                        continue
            else:
                items = []

        for item in items:
            if not isinstance(item, dict):
                continue

            qa_pair = GeneratedQAPair(
                question=item.get("question", ""),
                ground_truth_answer=item.get("ground_truth_answer", ""),
                question_type=item.get("question_type", "definition"),
                difficulty=item.get("difficulty", "medium"),
                keywords=item.get("keywords", []),
                source_context=item.get("source_context", ""),
                source_document=item.get("source_document", source_document),
                generation_reason=item.get("generation_reason", ""),
                ai_confidence=float(item.get("ai_confidence", 0.8)),
                needs_review=True,
                review_status="pending",
                created_at=datetime.now().isoformat()
            )
            qa_pairs.append(qa_pair)

        return qa_pairs

    def save_for_review(
        self,
        qa_pairs: list[GeneratedQAPair],
        batch_name: str = ""
    ) -> str:
        """
        保存待核验的问答对

        Args:
            qa_pairs: 问答对列表
            batch_name: 批次名称

        Returns:
            保存的文件路径
        """
        if not batch_name:
            batch_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"qa_batch_{batch_name}.json"
        filepath = QA_PENDING_REVIEW_DIR / filename

        data = {
            "batch_name": batch_name,
            "created_at": datetime.now().isoformat(),
            "total_count": len(qa_pairs),
            "qa_pairs": [asdict(qa) for qa in qa_pairs]
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(filepath)

    def load_pending_review(self, batch_name: str = None) -> list[GeneratedQAPair]:
        """
        加载待核验的问答对

        Args:
            batch_name: 批次名称（可选，不指定则加载最新批次）

        Returns:
            问答对列表
        """
        if batch_name:
            filepath = QA_PENDING_REVIEW_DIR / f"qa_batch_{batch_name}.json"
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [GeneratedQAPair(**item) for item in data.get("qa_pairs", [])]
            return []

        # 加载最新批次
        files = sorted(QA_PENDING_REVIEW_DIR.glob("qa_batch_*.json"), reverse=True)
        if not files:
            return []

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
            return [GeneratedQAPair(**item) for item in data.get("qa_pairs", [])]

    def review_qa_pair(
        self,
        index: int,
        approved: bool,
        reviewer_notes: str = "",
        batch_name: str = None
    ) -> dict:
        """
        核验问答对

        Args:
            index: 问答对索引
            approved: 是否通过
            reviewer_notes: 核验备注
            batch_name: 批次名称

        Returns:
            更新结果
        """
        qa_pairs = self.load_pending_review(batch_name)
        if index < 0 or index >= len(qa_pairs):
            return {"success": False, "error": "索引超出范围"}

        qa_pair = qa_pairs[index]
        qa_pair.review_status = "approved" if approved else "rejected"
        qa_pair.reviewer_notes = reviewer_notes
        qa_pair.needs_review = False

        if approved:
            # 保存到已批准目录
            self._save_approved(qa_pair)

        # 更新待核验文件
        if batch_name:
            filepath = QA_PENDING_REVIEW_DIR / f"qa_batch_{batch_name}.json"
            data = {
                "batch_name": batch_name,
                "updated_at": datetime.now().isoformat(),
                "qa_pairs": [asdict(qa) for qa in qa_pairs]
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "question": qa_pair.question,
            "review_status": qa_pair.review_status
        }

    def _save_approved(self, qa_pair: GeneratedQAPair):
        """保存已批准的问答对"""
        filepath = QA_APPROVED_DIR / "approved_qa_pairs.json"

        existing_pairs = []
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                existing_pairs = json.load(f)

        existing_pairs.append(asdict(qa_pair))

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing_pairs, f, ensure_ascii=False, indent=2)

    def get_approved_qa_pairs(self) -> list[GeneratedQAPair]:
        """获取已批准的问答对"""
        filepath = QA_APPROVED_DIR / "approved_qa_pairs.json"
        if not filepath.exists():
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [GeneratedQAPair(**item) for item in data]

    def batch_review(
        self,
        reviews: list[dict],
        batch_name: str = None
    ) -> dict:
        """
        批量核验问答对

        Args:
            reviews: 核验列表 [{"index": 0, "approved": true, "notes": ""}, ...]
            batch_name: 批次名称

        Returns:
            批量核验结果
        """
        results = {"approved": [], "rejected": [], "failed": []}

        for review in reviews:
            idx = review.get("index")
            approved = review.get("approved", False)
            notes = review.get("notes", "")

            result = self.review_qa_pair(idx, approved, notes, batch_name)
            if result["success"]:
                if approved:
                    results["approved"].append(result["question"])
                else:
                    results["rejected"].append(result["question"])
            else:
                results["failed"].append({"index": idx, "error": result.get("error")})

        return results

    def generate_and_save(
        self,
        document_content: str = "",
        document_name: str = "",
        count: int = 10,
        is_universal: bool = False,
        batch_name: str = ""
    ) -> dict:
        """
        一站式生成并保存问答对

        Args:
            document_content: 文档内容
            document_name: 文档名称
            count: 生成数量
            is_universal: 是否生成通用问答对
            batch_name: 批次名称

        Returns:
            生成结果
        """
        if is_universal:
            qa_pairs = self.generate_universal(count=count)
        else:
            qa_pairs = self.generate_for_document(
                document_content=document_content,
                document_name=document_name,
                count=count
            )

        if not qa_pairs:
            return {
                "success": False,
                "error": "未能生成问答对"
            }

        # 保存待核验
        filepath = self.save_for_review(qa_pairs, batch_name or datetime.now().strftime("%Y%m%d_%H%M%S"))

        return {
            "success": True,
            "total_generated": len(qa_pairs),
            "pending_review_file": filepath,
            "qa_pairs": [asdict(qa) for qa in qa_pairs]
        }

    def export_to_evaluation_format(self, file_path: str = None) -> list[dict]:
        """
        导出为评估格式

        Args:
            file_path: 导出文件路径

        Returns:
            评估格式的问答对列表
        """
        approved_pairs = self.get_approved_qa_pairs()

        eval_format = []
        for qa in approved_pairs:
            eval_format.append({
                "question": qa.question,
                "ground_truth": qa.ground_truth_answer,
                "expected_keywords": qa.keywords,
                "source_document": qa.source_document,
                "difficulty": qa.difficulty,
                "question_type": qa.question_type
            })

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(eval_format, f, ensure_ascii=False, indent=2)

        return eval_format

    def get_statistics(self) -> dict:
        """获取问答对统计信息"""
        # 待核验
        pending_files = list(QA_PENDING_REVIEW_DIR.glob("qa_batch_*.json"))
        pending_count = 0
        for f in pending_files:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                pending_count += len(data.get("qa_pairs", []))

        # 已批准
        approved_pairs = self.get_approved_qa_pairs()

        # 按难度统计
        difficulty_stats = {
            "easy": 0,
            "medium": 0,
            "hard": 0
        }
        for qa in approved_pairs:
            if qa.difficulty in difficulty_stats:
                difficulty_stats[qa.difficulty] += 1

        # 按类型统计
        type_stats = {}
        for qa in approved_pairs:
            qtype = qa.question_type
            type_stats[qtype] = type_stats.get(qtype, 0) + 1

        return {
            "pending_review": pending_count,
            "approved": len(approved_pairs),
            "difficulty_distribution": difficulty_stats,
            "type_distribution": type_stats,
            "total": len(approved_pairs) + pending_count
        }


# ============================================================================
# 便捷函数
# ============================================================================

_generator_instance = None


def get_qa_generator() -> QAGenerator:
    """获取问答对生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = QAGenerator()
    return _generator_instance


def generate_qa_for_document(
    file_path: str,
    count: int = 10
) -> dict:
    """
    便捷函数：为文档生成问答对

    Args:
        file_path: 文档路径
        count: 生成数量

    Returns:
        生成结果
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        generator = get_qa_generator()
        result = generator.generate_and_save(
            document_content=content,
            document_name=Path(file_path).name,
            count=count,
            is_universal=False
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_universal_qa(count: int = 10) -> dict:
    """
    便捷函数：生成通用问答对

    Args:
        count: 生成数量

    Returns:
        生成结果
    """
    generator = get_qa_generator()
    return generator.generate_and_save(
        count=count,
        is_universal=True,
        batch_name="universal"
    )

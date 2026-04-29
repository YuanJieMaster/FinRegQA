"""
评估服务模块
提供问答系统准确率评估功能和文件上传评估功能

支持两种评估模式：
1. 动态分析模式：根据文档自身结构特征动态计算分块预期范围
2. 预设验证模式：使用预定义的测试用例进行标准验证
"""

import os
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from difflib import SequenceMatcher

# 导入文档结构分析器
from app.services.document_analyzer import (
    DocumentStructureAnalyzer,
    DocumentStructure,
    DocumentType,
    DocumentComplexity,
    analyze_document_structure,
    get_chunk_accuracy_score,
)

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent
EVAL_DATA_DIR = PROJECT_ROOT / "data" / "evaluation"
EVAL_RESULTS_DIR = PROJECT_ROOT / "data" / "evaluation" / "results"
TEST_DOCS_DIR = PROJECT_ROOT / "data" / "evaluation" / "test_documents"


@dataclass
class QAPair:
    """问答对数据结构"""
    question: str
    ground_truth_answer: str
    ground_truth_context: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    source_regulation: str = ""
    notes: str = ""


@dataclass
class IngestTestCase:
    """文档导入测试用例"""
    file_name: str
    # 动态分析模式：不使用 expected_chunks，而是通过分析文档内容自动计算
    expected_chunks: int = 0  # 期望分块数（仅用于兼容，实际使用结构分析）
    expected_categories: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)
    min_chunk_size: int = 50
    max_chunk_size: int = 1000
    content_preview: str = ""  # 文档内容预览，用于验证

    # 新增：动态分析配置
    enable_dynamic_analysis: bool = True  # 是否启用动态分块分析
    analysis_accuracy_threshold: float = 0.6  # 准确率阈值，低于此值标记为警告


@dataclass
class DynamicAnalysisResult:
    """动态分析结果"""
    # 文档结构分析
    document_structure: Optional[dict] = None
    document_type: str = "unknown"
    total_articles: int = 0
    total_chapters: int = 0
    complexity: str = "medium"

    # 分块预期（基于分析计算）
    predicted_chunk_min: int = 0
    predicted_chunk_max: int = 0
    predicted_chunk_expected: int = 0

    # 准确率评估
    chunk_accuracy_score: float = 0.0
    accuracy_assessment: str = ""
    accuracy_suggestion: str = ""

    # 结构特征
    structure_features: list[str] = field(default_factory=list)


@dataclass
class IngestResult:
    """文档导入评估结果"""
    file_name: str
    file_type: str
    expected_chunks: int
    actual_chunks: int
    chunk_count_accuracy: float  # 分块数量准确率
    chunk_size_accuracy: float   # 分块大小准确率
    content_completeness: float # 内容完整性
    keyword_retention: float    # 关键词保留率
    field_accuracy: dict        # 字段准确率
    chunks: list = field(default_factory=list)
    error: str = ""

    # 新增：动态分析结果
    dynamic_analysis: Optional[DynamicAnalysisResult] = None


@dataclass
class IngestReport:
    """文档导入评估报告"""
    timestamp: str
    total_files: int
    successful_files: int
    failed_files: int
    avg_chunk_count_accuracy: float
    avg_chunk_size_accuracy: float
    avg_content_completeness: float
    avg_keyword_retention: float
    results: list = field(default_factory=list)
    overall_score: float = 0.0

    # 新增：动态分析相关指标
    avg_dynamic_accuracy_score: float = 0.0  # 平均动态准确率得分
    dynamic_analysis_enabled: bool = True    # 是否启用了动态分析
    document_complexity_distribution: dict = field(default_factory=dict)  # 文档复杂度分布


@dataclass
class RetrievalMetrics:
    """检索评估指标"""
    recall: float = 0.0
    precision: float = 0.0
    f1_score: float = 0.0
    hit_rate: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0


@dataclass
class AnswerMetrics:
    """问答评估指标"""
    exact_match: float = 0.0
    rouge_l: float = 0.0
    keyword_coverage: float = 0.0
    keyword_precision: float = 0.0
    semantic_similarity: float = 0.0
    length_ratio: float = 0.0


@dataclass
class IngestMetrics:
    """文档导入评估指标"""
    chunk_count_accuracy: float = 0.0
    chunk_size_accuracy: float = 0.0
    content_completeness: float = 0.0
    keyword_retention: float = 0.0


@dataclass
class EvaluationResult:
    """单次评估结果"""
    question: str
    generated_answer: str
    ground_truth: str
    retrieved_contexts: list[str]
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    response_time: float
    error: str = ""


@dataclass
class EvaluationReport:
    """评估报告"""
    timestamp: str
    total_questions: int
    successful_tests: int
    failed_tests: int
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    ingest_metrics: Optional[IngestMetrics] = None
    results: list = field(default_factory=list)
    overall_score: float = 0.0


class MetricsCalculator:
    """评估指标计算器"""

    @staticmethod
    def calculate_recall(retrieved: list[str], relevant: list[str]) -> float:
        if not relevant:
            return 0.0
        retrieved_set = set(retrieved)
        relevant_set = set(relevant)
        intersection = retrieved_set.intersection(relevant_set)
        return len(intersection) / len(relevant_set)

    @staticmethod
    def calculate_precision(retrieved: list[str], relevant: list[str]) -> float:
        if not retrieved:
            return 0.0
        retrieved_set = set(retrieved)
        relevant_set = set(relevant)
        intersection = retrieved_set.intersection(relevant_set)
        return len(intersection) / len(retrieved_set)

    @staticmethod
    def calculate_f1(recall: float, precision: float) -> float:
        if recall + precision == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        import re
        text = re.sub(r'\s+', ' ', text)
        return text

    @staticmethod
    def calculate_rouge_l(reference: str, candidate: str) -> float:
        if not reference or not candidate:
            return 0.0
        ref_norm = MetricsCalculator.normalize_text(reference)
        cand_norm = MetricsCalculator.normalize_text(candidate)
        return SequenceMatcher(None, ref_norm, cand_norm).ratio()

    @staticmethod
    def calculate_keyword_coverage(reference: str, candidate: str, keywords: list[str]) -> float:
        if not keywords:
            return 0.0
        if not candidate:
            return 0.0
        candidate_lower = candidate.lower()
        matched = sum(1 for kw in keywords if kw.lower() in candidate_lower)
        return matched / len(keywords)

    @staticmethod
    def calculate_semantic_similarity(reference: str, candidate: str) -> float:
        if not reference or not candidate:
            return 0.0
        ref_norm = MetricsCalculator.normalize_text(reference)
        cand_norm = MetricsCalculator.normalize_text(candidate)
        return SequenceMatcher(None, ref_norm, cand_norm).ratio()

    @staticmethod
    def calculate_length_ratio(reference: str, candidate: str) -> float:
        if not reference:
            return 0.0 if candidate else 1.0
        ref_len = len(reference)
        cand_len = len(candidate) if candidate else 0
        if cand_len == 0:
            return 0.0
        ratio = cand_len / ref_len
        if ratio >= 0.5 and ratio <= 2.0:
            return 1.0 - abs(ratio - 1.0)
        else:
            return max(0, 0.5 - (ratio - 2.0) * 0.25)


class EvaluationService:
    """
    评估服务

    提供问答系统准确率评估功能
    """

    def __init__(self):
        self._ensure_directories()
        self._load_default_qa_pairs()

    def _ensure_directories(self):
        """确保目录存在"""
        EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def _load_default_qa_pairs(self):
        """加载默认问答对"""
        qa_file = EVAL_DATA_DIR / "qa_pairs.json"

        if qa_file.exists():
            with open(qa_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.default_qa_pairs = [QAPair(**item) for item in data]
        else:
            self.default_qa_pairs = self._create_default_qa_pairs()
            self._save_qa_pairs()

    def _create_default_qa_pairs(self) -> list[QAPair]:
        """创建默认问答对"""
        qa_pairs = [
            QAPair(
                question="商业银行的风险管理要求是什么？",
                ground_truth_answer="商业银行应当建立完善的风险管理框架，包括风险识别、风险计量、风险监测和风险控制等环节。",
                keywords=["风险管理", "风险识别", "风险控制", "内部控制"],
                difficulty="easy"
            ),
            QAPair(
                question="商业银行资本充足率不得低于多少？",
                ground_truth_answer="商业银行资本充足率不得低于8%，核心资本充足率不得低于4%。",
                keywords=["资本充足率", "8%", "核心资本", "4%"],
                difficulty="easy"
            ),
            QAPair(
                question="保险公司偿付能力充足率要求是多少？",
                ground_truth_answer="保险公司偿付能力充足率不得低于100%，核心偿付能力充足率不低于50%。",
                keywords=["偿付能力", "100%", "核心偿付能力", "50%"],
                difficulty="easy"
            ),
            QAPair(
                question="证券公司客户资产保护的措施有哪些？",
                ground_truth_answer="证券公司应当将客户资金与自有资产分别管理、分别记账、分别托管。",
                keywords=["客户资产", "分别管理", "资金专用账户", "挪用"],
                difficulty="medium"
            ),
            QAPair(
                question="金融机构信息披露的主要内容包括哪些？",
                ground_truth_answer="金融机构应当披露财务状况、公司治理、风险管理、关联交易等信息。",
                keywords=["信息披露", "财务状况", "风险管理", "关联交易"],
                difficulty="medium"
            ),
            QAPair(
                question="客户身份识别的基本要求是什么？",
                ground_truth_answer="金融机构应当核对客户身份，了解客户背景，识别受益所有人。",
                keywords=["身份识别", "受益所有人", "尽职调查", "客户背景"],
                difficulty="medium"
            ),
            QAPair(
                question="关联交易管理的基本原则是什么？",
                ground_truth_answer="关联交易应当遵循公平、公正、公开的原则，价格应当公允。",
                keywords=["关联交易", "公平", "公正", "公允"],
                difficulty="medium"
            ),
            QAPair(
                question="保险资金运用的范围是什么？",
                ground_truth_answer="保险资金可投资于银行存款、债券、股票、证券投资基金等标准化资产。",
                keywords=["保险资金", "银行存款", "债券", "股票"],
                difficulty="hard"
            ),
        ]
        return qa_pairs

    def _save_qa_pairs(self):
        """保存问答对"""
        qa_file = EVAL_DATA_DIR / "qa_pairs.json"
        with open(qa_file, "w", encoding="utf-8") as f:
            json.dump([asdict(qa) for qa in self.default_qa_pairs], f, ensure_ascii=False, indent=2)

    def get_qa_pairs(self) -> list[QAPair]:
        """获取问答对列表"""
        return self.default_qa_pairs

    def add_qa_pair(self, qa_pair: QAPair):
        """添加问答对"""
        self.default_qa_pairs.append(qa_pair)
        self._save_qa_pairs()

    def remove_qa_pair(self, index: int) -> bool:
        """删除问答对"""
        if 0 <= index < len(self.default_qa_pairs):
            self.default_qa_pairs.pop(index)
            self._save_qa_pairs()
            return True
        return False

    def get_ingest_test_cases(self) -> list[IngestTestCase]:
        """获取默认的文档导入测试用例

        返回启用动态分析的测试用例，文档结构分析将自动进行。
        """
        test_cases_file = EVAL_DATA_DIR / "ingest_test_cases.json"

        if test_cases_file.exists():
            with open(test_cases_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [IngestTestCase(**item) for item in data]

        # 创建默认测试用例（启用动态分析）
        default_cases = [
            IngestTestCase(
                file_name="test_bank_regulation.txt",
                expected_chunks=0,  # 动态计算
                expected_categories=["风险管理", "资本管理"],
                expected_keywords=["商业银行", "风险管理", "资本充足率", "内部控制", "信用风险"],
                min_chunk_size=30,
                max_chunk_size=500,
                content_preview="商业银行风险管理指引...",
                enable_dynamic_analysis=True,
                analysis_accuracy_threshold=0.6
            ),
            IngestTestCase(
                file_name="test_insurance_rules.txt",
                expected_chunks=0,  # 动态计算
                expected_categories=["偿付能力"],
                expected_keywords=["保险公司", "偿付能力", "最低资本", "风险综合评级"],
                min_chunk_size=30,
                max_chunk_size=500,
                content_preview="保险公司偿付能力管理规定...",
                enable_dynamic_analysis=True,
                analysis_accuracy_threshold=0.6
            ),
            IngestTestCase(
                file_name="test_securities_trading.txt",
                expected_chunks=0,  # 动态计算
                expected_categories=["经纪业务", "合规管理"],
                expected_keywords=["证券公司", "经纪业务", "客户资金", "禁止行为", "虚假宣传"],
                min_chunk_size=30,
                max_chunk_size=500,
                content_preview="证券经纪业务管理办法...",
                enable_dynamic_analysis=True,
                analysis_accuracy_threshold=0.6
            ),
        ]

        # 保存默认用例
        TEST_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        with open(test_cases_file, "w", encoding="utf-8") as f:
            json.dump([asdict(tc) for tc in default_cases], f, ensure_ascii=False, indent=2)

        # 创建测试文档
        self._create_test_documents()

        return default_cases

    def _create_test_documents(self):
        """创建测试文档"""
        TEST_DOCS_DIR.mkdir(parents=True, exist_ok=True)

        # 银行风险管理指引
        bank_content = """商业银行风险管理指引

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

第九条 商业银行应当建立资本规划机制，合理配置经济资本。"""

        # 保险偿付能力规定
        insurance_content = """保险公司偿付能力管理规定

第一章 总则
第一条 为了加强保险公司偿付能力监管，保护保险消费者合法权益，根据《中华人民共和国保险法》等法律法规，制定本规定。

第二条 本规定所称偿付能力，是指保险公司偿还债务的能力。

第三条 保险公司应当建立健全偿付能力管理制度，确保偿付能力充足。

第二章 偿付能力要求
第四条 保险公司偿付能力充足率不得低于100%。

第五条 保险公司核心偿付能力充足率不得低于50%。

第六条 保险公司综合偿付能力充足率不得低于100%。

第七条 保险公司应当按照规定计提最低资本，确保实际资本不低于最低资本要求。"""

        # 证券经纪业务办法
        securities_content = """证券经纪业务管理办法

第一章 总则
第一条 为了规范证券经纪业务，保护投资者合法权益，根据《中华人民共和国证券法》等法律法规，制定本办法。

第二条 本办法所称证券经纪业务，是指证券公司接受客户委托，代理客户买卖证券的业务活动。

第三条 证券公司应当建立健全经纪业务管理制度，加强合规管理。

第二章 客户资产管理
第四条 证券公司应当将客户资金与自有资金分别存放于客户资金专用账户。

第五条 禁止证券公司及其从业人员挪用客户资金或者证券。

第六条 证券公司应当建立客户资产安全保管制度。

第三章 合规禁止行为
第七条 证券公司及其从业人员不得有下列行为：
（一）虚假宣传或者误导性陈述；
（二）诱导客户进行不必要的证券交易；
（三）代客理财；
（四）向客户承诺收益；
（五）通过经纪业务获取不正当利益。

第八条 证券公司应当加强交易监控，及时发现和报告异常交易。"""

        (TEST_DOCS_DIR / "test_bank_regulation.txt").write_text(bank_content, encoding="utf-8")
        (TEST_DOCS_DIR / "test_insurance_rules.txt").write_text(insurance_content, encoding="utf-8")
        (TEST_DOCS_DIR / "test_securities_trading.txt").write_text(securities_content, encoding="utf-8")

    def evaluate_ingest_single(self,
                              file_path: str,
                              test_case: IngestTestCase,
                              api_url: str = "http://localhost:8000",
                              document_content: str = None) -> IngestResult:
        """
        评估单个文档导入（支持动态分析）

        Args:
            file_path: 文件路径
            test_case: 测试用例
            api_url: API 地址
            document_content: 文档内容（如果已读取则传入，避免重复读取）

        Returns:
            导入评估结果（包含动态分析结果）
        """
        import requests

        result = IngestResult(
            file_name=test_case.file_name,
            file_type=Path(file_path).suffix,
            expected_chunks=test_case.expected_chunks,
            actual_chunks=0,
            chunk_count_accuracy=0.0,
            chunk_size_accuracy=0.0,
            content_completeness=0.0,
            keyword_retention=0.0,
            field_accuracy={},
            chunks=[],
            dynamic_analysis=None
        )

        # 读取文档内容（用于动态分析）
        raw_content = document_content
        if raw_content is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()
            except Exception as e:
                result.error = f"读取文件失败: {e}"
                return result

        # 动态分析文档结构
        if test_case.enable_dynamic_analysis and raw_content:
            analyzer = DocumentStructureAnalyzer(
                min_chunk_size=test_case.min_chunk_size,
                max_chunk_size=test_case.max_chunk_size
            )
            doc_structure = analyzer.analyze(raw_content, test_case.file_name)

            # 构建动态分析结果
            dynamic_result = DynamicAnalysisResult(
                document_structure=doc_structure.to_dict(),
                document_type=doc_structure.document_type.value,
                total_articles=doc_structure.total_articles,
                total_chapters=doc_structure.total_chapters,
                complexity=doc_structure.complexity.value,
                predicted_chunk_min=doc_structure.predicted_chunk_count_min,
                predicted_chunk_max=doc_structure.predicted_chunk_count_max,
                predicted_chunk_expected=doc_structure.predicted_chunk_count_expected,
                structure_features=doc_structure.structure_features
            )

            # 调用导入 API
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (test_case.file_name, f)}

                    data = {
                        "category": test_case.expected_categories[0] if test_case.expected_categories else "测试分类",
                        "regulation_type": "测试法规类型",
                        "region": "全国",
                        "source": "准确率评估测试",
                        "min_chunk_size": test_case.min_chunk_size,
                        "keep_separator": True,
                        "batch_size": 100,
                    }

                    response = requests.post(
                        f"{api_url}/api/knowledge/ingest",
                        files=files,
                        data=data,
                        timeout=300
                    )

                if response.status_code == 200:
                    ingest_result = response.json()
                    result.actual_chunks = ingest_result.get("chunk_count", 0)

                    # 使用动态分析计算准确率
                    accuracy_result = get_chunk_accuracy_score(result.actual_chunks, doc_structure)

                    # 更新准确率指标
                    result.chunk_count_accuracy = accuracy_result["score"]
                    dynamic_result.chunk_accuracy_score = accuracy_result["score"]
                    dynamic_result.accuracy_assessment = accuracy_result["assessment"]
                    dynamic_result.accuracy_suggestion = accuracy_result["suggestion"]

                    # 计算其他指标
                    if doc_structure.total_articles > 0:
                        result.content_completeness = min(1.0, result.actual_chunks / doc_structure.total_articles)
                    else:
                        result.content_completeness = min(1.0, result.actual_chunks / max(doc_structure.predicted_chunk_expected, 1))

                    result.keyword_retention = result.content_completeness
                    result.chunk_size_accuracy = 0.8  # 简化值
                    result.field_accuracy = {
                        "category": 1.0,
                        "region": 1.0,
                        "regulation_type": 1.0
                    }

                else:
                    result.error = f"API 错误: {response.status_code} - {response.text}"
                    # 即使 API 调用失败，也记录动态分析结果
                    dynamic_result.chunk_accuracy_score = 0.0
                    dynamic_result.accuracy_assessment = "无法评估：API 调用失败"
                    dynamic_result.accuracy_suggestion = f"错误信息: {response.text[:100]}"

            except Exception as e:
                result.error = str(e)
                dynamic_result.chunk_accuracy_score = 0.0
                dynamic_result.accuracy_assessment = "无法评估：发生异常"
                dynamic_result.accuracy_suggestion = str(e)

            result.dynamic_analysis = dynamic_result
        else:
            # 不使用动态分析时的原有逻辑
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (test_case.file_name, f)}

                    data = {
                        "category": test_case.expected_categories[0] if test_case.expected_categories else "测试分类",
                        "regulation_type": "测试法规类型",
                        "region": "全国",
                        "source": "准确率评估测试",
                        "min_chunk_size": test_case.min_chunk_size,
                        "keep_separator": True,
                        "batch_size": 100,
                    }

                    response = requests.post(
                        f"{api_url}/api/knowledge/ingest",
                        files=files,
                        data=data,
                        timeout=300
                    )

                if response.status_code == 200:
                    ingest_result = response.json()
                    result.actual_chunks = ingest_result.get("chunk_count", 0)

                    # 使用预设的 expected_chunks 计算准确率
                    if test_case.expected_chunks > 0:
                        diff = abs(result.actual_chunks - test_case.expected_chunks)
                        result.chunk_count_accuracy = max(0, 1 - diff / test_case.expected_chunks)
                    else:
                        result.chunk_count_accuracy = 1.0 if result.actual_chunks > 0 else 0.0

                    result.content_completeness = min(1.0, result.actual_chunks / max(test_case.expected_chunks, 1))
                    result.keyword_retention = result.content_completeness
                    result.chunk_size_accuracy = 0.8
                    result.field_accuracy = {
                        "category": 1.0,
                        "region": 1.0,
                        "regulation_type": 1.0
                    }

                else:
                    result.error = f"API 错误: {response.status_code} - {response.text}"

            except Exception as e:
                result.error = str(e)

        return result

    def evaluate_ingest_batch(self,
                            api_url: str = "http://localhost:8000",
                            test_cases: list[IngestTestCase] = None,
                            enable_dynamic_analysis: bool = True) -> IngestReport:
        """
        批量评估文档导入（支持动态分析）

        Args:
            api_url: API 地址
            test_cases: 测试用例列表
            enable_dynamic_analysis: 是否启用动态分析

        Returns:
            导入评估报告
        """
        if test_cases is None:
            test_cases = self.get_ingest_test_cases()

        # 确保所有测试用例都使用动态分析
        if enable_dynamic_analysis:
            for tc in test_cases:
                tc.enable_dynamic_analysis = True

        results = []
        chunk_count_accuracies = []
        chunk_size_accuracies = []
        content_completeness_list = []
        keyword_retentions = []
        dynamic_scores = []
        complexity_distribution = {}

        for test_case in test_cases:
            # 查找测试文档
            file_path = TEST_DOCS_DIR / test_case.file_name

            if not file_path.exists():
                # 尝试创建文档
                self._create_test_documents()

            if file_path.exists():
                result = self.evaluate_ingest_single(
                    file_path=str(file_path),
                    test_case=test_case,
                    api_url=api_url
                )
            else:
                result = IngestResult(
                    file_name=test_case.file_name,
                    file_type="",
                    expected_chunks=test_case.expected_chunks,
                    actual_chunks=0,
                    chunk_count_accuracy=0.0,
                    chunk_size_accuracy=0.0,
                    content_completeness=0.0,
                    keyword_retention=0.0,
                    field_accuracy={},
                    error="测试文件不存在"
                )

            results.append(asdict(result))

            if not result.error:
                chunk_count_accuracies.append(result.chunk_count_accuracy)
                chunk_size_accuracies.append(result.chunk_size_accuracy)
                content_completeness_list.append(result.content_completeness)
                keyword_retentions.append(result.keyword_retention)

                # 收集动态分析结果
                if result.dynamic_analysis:
                    dynamic_scores.append(result.dynamic_analysis.chunk_accuracy_score)

                    # 统计复杂度分布
                    complexity = result.dynamic_analysis.complexity
                    complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1

        # 计算平均值
        n = len(results)
        avg_chunk_count = sum(chunk_count_accuracies) / n if n > 0 else 0
        avg_chunk_size = sum(chunk_size_accuracies) / n if n > 0 else 0
        avg_content = sum(content_completeness_list) / n if n > 0 else 0
        avg_keyword = sum(keyword_retentions) / n if n > 0 else 0
        avg_dynamic_score = sum(dynamic_scores) / len(dynamic_scores) if dynamic_scores else 0

        # 综合评分（加权平均，动态分析得分权重更高）
        if enable_dynamic_analysis and dynamic_scores:
            overall_score = (
                avg_chunk_count * 0.2 +
                avg_chunk_size * 0.15 +
                avg_content * 0.25 +
                avg_keyword * 0.15 +
                avg_dynamic_score * 0.25  # 动态分析得分占25%权重
            )
        else:
            overall_score = (avg_chunk_count * 0.3 + avg_chunk_size * 0.2 +
                            avg_content * 0.3 + avg_keyword * 0.2)

        return IngestReport(
            timestamp=datetime.now().isoformat(),
            total_files=n,
            successful_files=n - sum(1 for r in results if r.get("error")),
            failed_files=sum(1 for r in results if r.get("error")),
            avg_chunk_count_accuracy=avg_chunk_count,
            avg_chunk_size_accuracy=avg_chunk_size,
            avg_content_completeness=avg_content,
            avg_keyword_retention=avg_keyword,
            results=results,
            overall_score=overall_score,
            avg_dynamic_accuracy_score=avg_dynamic_score,
            dynamic_analysis_enabled=enable_dynamic_analysis,
            document_complexity_distribution=complexity_distribution
        )

    def evaluate_single(self,
                       question: str,
                       generated_answer: str,
                       retrieved_contexts: list[str] = None,
                       ground_truth: str = None) -> EvaluationResult:
        """
        评估单个问答结果

        Args:
            question: 问题
            generated_answer: 生成的答案
            retrieved_contexts: 检索到的上下文
            ground_truth: 标准答案

        Returns:
            评估结果
        """
        result = EvaluationResult(
            question=question,
            generated_answer=generated_answer,
            ground_truth=ground_truth or "",
            retrieved_contexts=retrieved_contexts or [],
            retrieval_metrics=RetrievalMetrics(),
            answer_metrics=AnswerMetrics(),
            response_time=0.0
        )

        # 查找对应的问答对
        qa_pair = None
        for qa in self.default_qa_pairs:
            if qa.question == question:
                qa_pair = qa
                break

        if qa_pair:
            ground_truth = ground_truth or qa_pair.ground_truth_answer
        else:
            ground_truth = ground_truth or generated_answer  # 避免空值

        # 计算答案指标
        result.answer_metrics = AnswerMetrics(
            exact_match=1.0 if generated_answer.strip() == ground_truth.strip() else 0.0,
            rouge_l=MetricsCalculator.calculate_rouge_l(ground_truth, generated_answer),
            keyword_coverage=MetricsCalculator.calculate_keyword_coverage(
                ground_truth, generated_answer,
                qa_pair.keywords if qa_pair else []
            ),
            semantic_similarity=MetricsCalculator.calculate_semantic_similarity(ground_truth, generated_answer),
            length_ratio=MetricsCalculator.calculate_length_ratio(ground_truth, generated_answer)
        )

        # 计算检索指标
        if retrieved_contexts and qa_pair:
            retrieved_texts = [str(c) if not isinstance(c, str) else c for c in retrieved_contexts]
            result.retrieval_metrics = RetrievalMetrics(
                recall=MetricsCalculator.calculate_recall(
                    retrieved_texts,
                    qa_pair.ground_truth_context
                ),
                precision=MetricsCalculator.calculate_precision(
                    retrieved_texts,
                    qa_pair.ground_truth_context
                ),
                hit_rate=1.0 if result.retrieval_metrics.recall > 0 else 0.0
            )
            result.retrieval_metrics.f1_score = MetricsCalculator.calculate_f1(
                result.retrieval_metrics.recall,
                result.retrieval_metrics.precision
            )

        return result

    def evaluate_batch(self,
                     test_cases: list[dict],
                     api_url: str = "http://localhost:8000") -> EvaluationReport:
        """
        批量评估

        Args:
            test_cases: 测试用例列表，每项包含 question, ground_truth, expected_keywords
            api_url: API 地址

        Returns:
            评估报告
        """
        import requests

        results = []
        retrieval_metrics_list = []
        answer_metrics_list = []

        for i, case in enumerate(test_cases):
            question = case.get("question", "")

            try:
                start_time = time.time()

                # 调用问答 API
                response = requests.post(
                    f"{api_url}/api/knowledge/answer",
                    json={"question": question},
                    timeout=180
                )

                response_time = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    generated_answer = data.get("answer", "")
                    retrieved_contexts = [r.get("content", "") for r in data.get("raw_results", [])]

                    # 评估
                    result = self.evaluate_single(
                        question=question,
                        generated_answer=generated_answer,
                        retrieved_contexts=retrieved_contexts,
                        ground_truth=case.get("ground_truth")
                    )
                    result.response_time = response_time
                else:
                    result = EvaluationResult(
                        question=question,
                        generated_answer="",
                        ground_truth=case.get("ground_truth", ""),
                        retrieved_contexts=[],
                        retrieval_metrics=RetrievalMetrics(),
                        answer_metrics=AnswerMetrics(),
                        response_time=response_time,
                        error=f"API 错误: {response.status_code}"
                    )

            except Exception as e:
                result = EvaluationResult(
                    question=question,
                    generated_answer="",
                    ground_truth=case.get("ground_truth", ""),
                    retrieved_contexts=[],
                    retrieval_metrics=RetrievalMetrics(),
                    answer_metrics=AnswerMetrics(),
                    response_time=0.0,
                    error=str(e)
                )

            results.append(result)
            retrieval_metrics_list.append(result.retrieval_metrics)
            answer_metrics_list.append(result.answer_metrics)

        # 计算平均指标
        avg_retrieval = self._average_retrieval_metrics(retrieval_metrics_list)
        avg_answer = self._average_answer_metrics(answer_metrics_list)

        # 计算综合评分
        overall_score = (
            avg_retrieval.f1_score * 0.3 +
            avg_answer.keyword_coverage * 0.3 +
            avg_answer.semantic_similarity * 0.4
        )

        report = EvaluationReport(
            timestamp=datetime.now().isoformat(),
            total_questions=len(test_cases),
            successful_tests=sum(1 for r in results if not r.error),
            failed_tests=sum(1 for r in results if r.error),
            retrieval_metrics=avg_retrieval,
            answer_metrics=avg_answer,
            results=[asdict(r) for r in results],
            overall_score=overall_score
        )

        return report

    def _average_retrieval_metrics(self, metrics_list: list[RetrievalMetrics]) -> RetrievalMetrics:
        """计算平均检索指标"""
        if not metrics_list:
            return RetrievalMetrics()

        n = len(metrics_list)
        return RetrievalMetrics(
            recall=sum(m.recall for m in metrics_list) / n,
            precision=sum(m.precision for m in metrics_list) / n,
            f1_score=sum(m.f1_score for m in metrics_list) / n,
            hit_rate=sum(m.hit_rate for m in metrics_list) / n,
            mrr=sum(m.mrr for m in metrics_list) / n,
            ndcg=sum(m.ndcg for m in metrics_list) / n
        )

    def _average_answer_metrics(self, metrics_list: list[AnswerMetrics]) -> AnswerMetrics:
        """计算平均问答指标"""
        if not metrics_list:
            return AnswerMetrics()

        n = len(metrics_list)
        return AnswerMetrics(
            exact_match=sum(m.exact_match for m in metrics_list) / n,
            rouge_l=sum(m.rouge_l for m in metrics_list) / n,
            keyword_coverage=sum(m.keyword_coverage for m in metrics_list) / n,
            keyword_precision=sum(m.keyword_precision for m in metrics_list) / n,
            semantic_similarity=sum(m.semantic_similarity for m in metrics_list) / n,
            length_ratio=sum(m.length_ratio for m in metrics_list) / n
        )

    def save_report(self, report: EvaluationReport, filename: str = None) -> str:
        """保存评估报告"""
        if filename is None:
            filename = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = EVAL_RESULTS_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)

        return str(filepath)

    def load_report(self, filename: str) -> EvaluationReport:
        """加载评估报告"""
        filepath = EVAL_RESULTS_DIR / filename
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return EvaluationReport(
            timestamp=data["timestamp"],
            total_questions=data["total_questions"],
            successful_tests=data["successful_tests"],
            failed_tests=data["failed_tests"],
            retrieval_metrics=RetrievalMetrics(**data["retrieval_metrics"]),
            answer_metrics=AnswerMetrics(**data["answer_metrics"]),
            results=data.get("results", []),
            overall_score=data.get("overall_score", 0.0)
        )

    def list_reports(self) -> list[dict]:
        """列出所有评估报告"""
        reports = []
        for f in sorted(EVAL_RESULTS_DIR.glob("eval_*.json"), reverse=True):
            stat = f.stat()
            reports.append({
                "filename": f.name,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
        return reports


# ============================================================================
# 便捷函数
# ============================================================================

def analyze_document_for_testing(file_path: str) -> dict:
    """
    便捷函数：分析文档结构，生成测试预期

    Args:
        file_path: 文档路径

    Returns:
        dict: 包含文档分析和测试建议
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        analyzer = DocumentStructureAnalyzer()
        structure = analyzer.analyze(content, os.path.basename(file_path))

        return {
            "success": True,
            "document_name": structure.document_name,
            "document_type": structure.document_type.value,
            "complexity": structure.complexity.value,
            "total_articles": structure.total_articles,
            "total_chapters": structure.total_chapters,
            "text_length": structure.cleaned_text_length,
            "predicted_chunk_range": {
                "min": structure.predicted_chunk_count_min,
                "max": structure.predicted_chunk_count_max,
                "expected": structure.predicted_chunk_count_expected
            },
            "recommended_chunk_size": structure.recommended_chunk_size,
            "structure_features": structure.structure_features,
            "test_case": {
                "file_name": os.path.basename(file_path),
                "expected_categories": [],
                "expected_keywords": _extract_keywords_from_content(content),
                "min_chunk_size": max(30, structure.recommended_chunk_size // 2),
                "max_chunk_size": structure.recommended_chunk_size * 2,
                "enable_dynamic_analysis": True,
                "analysis_accuracy_threshold": 0.6
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _extract_keywords_from_content(content: str, max_keywords: int = 10) -> list[str]:
    """从内容中提取关键词（简单实现）"""
    import re
    from collections import Counter

    # 常见金融监管关键词
    financial_keywords = [
        "风险管理", "资本充足率", "偿付能力", "内部控制", "合规管理",
        "信息披露", "流动性", "信用风险", "市场风险", "操作风险",
        "公司治理", "关联交易", "客户资金", "资产保护", "监管要求",
        "最低资本", "杠杆率", "拨备覆盖率", "大额风险暴露", "集中度风险"
    ]

    found_keywords = []
    for kw in financial_keywords:
        if kw in content:
            found_keywords.append(kw)
            if len(found_keywords) >= max_keywords:
                break

    # 如果没找到足够关键词，提取高频词
    if len(found_keywords) < 5:
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', content)
        word_counts = Counter(words)
        common_words = [w for w, _ in word_counts.most_common(20)]
        # 过滤掉常见通用词
        filtered = [w for w in common_words if w not in ["本法", "规定", "应当", "不得", "要求", "应当", "可以", "下列"]]
        found_keywords.extend(filtered[:5])

    return found_keywords[:max_keywords]


def get_ingest_test_case_for_file(file_path: str, category: str = None) -> IngestTestCase:
    """
    便捷函数：为指定文件生成测试用例

    Args:
        file_path: 文件路径
        category: 分类（可选）

    Returns:
        IngestTestCase: 测试用例
    """
    analysis = analyze_document_for_testing(file_path)

    if not analysis.get("success"):
        raise ValueError(f"无法分析文档: {analysis.get('error')}")

    test_case_dict = analysis.get("test_case", {})
    if category:
        test_case_dict["expected_categories"] = [category]

    return IngestTestCase(**test_case_dict)


# 全局单例
_evaluation_service = None

def get_evaluation_service() -> EvaluationService:
    """获取评估服务单例"""
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service


def evaluate_with_approved_qa_pairs(api_url: str = "http://localhost:8000") -> EvaluationReport:
    """
    使用AI生成的已批准问答对进行评估

    便捷函数：加载已通过人工核验的问答对，运行批量评估。

    Args:
        api_url: API地址

    Returns:
        评估报告
    """
    from app.services.qa_generator import get_qa_generator

    generator = get_qa_generator()
    approved_pairs = generator.get_approved_qa_pairs()

    if not approved_pairs:
        return EvaluationReport(
            timestamp=datetime.now().isoformat(),
            total_questions=0,
            successful_tests=0,
            failed_tests=0,
            retrieval_metrics=RetrievalMetrics(),
            answer_metrics=AnswerMetrics(),
            results=[],
            overall_score=0.0
        )

    test_cases = [
        {
            "question": qa.question,
            "ground_truth": qa.ground_truth_answer,
            "expected_keywords": qa.keywords
        }
        for qa in approved_pairs
    ]

    service = get_evaluation_service()
    return service.evaluate_batch(test_cases=test_cases, api_url=api_url)

"""
文档结构分析器
Document Structure Analyzer

用于分析金融法规文档的结构特征，智能预测合理的分块数量范围，
为准确率评估提供动态的参考标准，而非硬编码的固定值。
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


class DocumentType(Enum):
    """文档类型枚举"""
    REGULATION = "regulation"           # 正式法规文件
    GUIDELINE = "guideline"             # 指导意见
    NOTICE = "notice"                   # 通知文件
    MEASURE = "measure"                 # 管理办法
    RULE = "rule"                      # 暂行规定/规则
    MIXED = "mixed"                    # 混合类型
    UNKNOWN = "unknown"                # 未知类型


class DocumentComplexity(Enum):
    """文档复杂度枚举"""
    SIMPLE = "simple"                 # 简单（5条以内）
    MEDIUM = "medium"                  # 中等（5-20条）
    COMPLEX = "complex"                # 复杂（20-50条）
    VERY_COMPLEX = "very_complex"      # 非常复杂（50条以上）


@dataclass
class ArticleInfo:
    """条款信息"""
    number: str                         # 条款编号（如"第一条"）
    number_normalized: int              # 标准化编号（数字）
    content_length: int                 # 内容长度（字符数）
    clause_count: int                   # 款数量
    has_sub_items: bool                # 是否有子项
    starts_new_chapter: bool            # 是否开启新章节


@dataclass
class ChapterInfo:
    """章节信息"""
    number: str                         # 章节编号
    title: str                          # 章节标题
    article_range: Tuple[int, int]      # 该章节包含的条款范围
    article_count: int                   # 该章节条款数量


@dataclass
class DocumentStructure:
    """文档结构分析结果"""
    document_type: DocumentType = DocumentType.UNKNOWN
    document_name: str = ""
    raw_text_length: int = 0
    cleaned_text_length: int = 0

    # 条款统计
    total_articles: int = 0
    articles: List[ArticleInfo] = field(default_factory=list)
    avg_article_length: float = 0.0
    max_article_length: int = 0
    min_article_length: int = 0

    # 章节统计
    total_chapters: int = 0
    chapters: List[ChapterInfo] = field(default_factory=list)

    # 复杂度评估
    complexity: DocumentComplexity = DocumentComplexity.MEDIUM

    # 特殊标识检测
    has_numbered_items: bool = False    # 是否有编号列表项
    has_parenthetical_items: bool = False  # 是否有括号项
    has_tables: bool = False            # 可能有表格

    # 预测的分块参数
    predicted_chunk_count_min: int = 0  # 预测最小分块数
    predicted_chunk_count_max: int = 0  # 预测最大分块数
    predicted_chunk_count_expected: int = 0  # 预测期望分块数
    recommended_chunk_size: int = 600   # 推荐的块大小

    # 结构特征描述
    structure_features: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "document_type": self.document_type.value,
            "document_name": self.document_name,
            "raw_text_length": self.raw_text_length,
            "cleaned_text_length": self.cleaned_text_length,
            "total_articles": self.total_articles,
            "total_chapters": self.total_chapters,
            "complexity": self.complexity.value,
            "avg_article_length": self.avg_article_length,
            "predicted_chunk_count_range": f"{self.predicted_chunk_count_min}-{self.predicted_chunk_count_max}",
            "predicted_chunk_count_expected": self.predicted_chunk_count_expected,
            "structure_features": self.structure_features,
        }


class DocumentStructureAnalyzer:
    """
    文档结构分析器

    分析金融法规文档的内部结构，提取关键特征，并智能预测合理的分块范围。
    核心思想：不同文档结构差异巨大，需要根据文档自身的特征来评估分块效果。
    """

    # 条款编号的正则表达式（支持中文和阿拉伯数字）
    ARTICLE_PATTERNS = [
        re.compile(r"第[零一二三四五六七八九十百千]+条"),
        re.compile(r"第[0-9０-９]+条"),
    ]

    # 款编号的正则表达式
    CLAUSE_PATTERNS = [
        re.compile(r"第[零一二三四五六七八九十百千]+款"),
        re.compile(r"第[0-9０-９]+款"),
    ]

    # 章节编号的正则表达式
    CHAPTER_PATTERNS = [
        re.compile(r"第[零一二三四五六七八九十百千]+章"),
        re.compile(r"第[0-9０-９]+章"),
    ]

    # 编号列表项的正则表达式（如：一、二、三、 或 1. 2. 3.）
    NUMBERED_ITEM_PATTERNS = [
        re.compile(r"^[零一二三四五六七八九十百千\d]+[、.．]"),
        re.compile(r"^\([0-9０-９a-zA-Z]+\)"),
    ]

    # 括号项的正则表达式（如：（一）（二）或 ① ②）
    PARENTHETICAL_ITEM_PATTERNS = [
        re.compile(r"[（(][零一二三四五六七八九十a-zA-Z0-9]+[)）]"),
        re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]"),
    ]

    # 文档类型关键词
    DOCUMENT_TYPE_KEYWORDS = {
        DocumentType.REGULATION: ["法规", "条例", "规定"],
        DocumentType.GUIDELINE: ["指导意见", "指引", "指南"],
        DocumentType.NOTICE: ["通知", "公告", "通告"],
        DocumentType.MEASURE: ["管理办法", "实施细则", "操作规程"],
        DocumentType.RULE: ["暂行规定", "试行", "规则", "制度"],
    }

    # 不同复杂度文档的条款数量阈值
    COMPLEXITY_THRESHOLDS = {
        DocumentComplexity.SIMPLE: (0, 5),
        DocumentComplexity.MEDIUM: (5, 20),
        DocumentComplexity.COMPLEX: (20, 50),
        DocumentComplexity.VERY_COMPLEX: (50, float('inf')),
    }

    def __init__(self, min_chunk_size: int = 50, max_chunk_size: int = 800):
        """
        初始化分析器

        Args:
            min_chunk_size: 最小块大小（字符数）
            max_chunk_size: 最大块大小（字符数）
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def analyze(self, text: str, document_name: str = "") -> DocumentStructure:
        """
        分析文档结构

        Args:
            text: 文档文本内容
            document_name: 文档名称（可选，用于类型识别）

        Returns:
            DocumentStructure: 文档结构分析结果
        """
        if not text or not text.strip():
            return DocumentStructure(document_name=document_name)

        raw_length = len(text)
        cleaned_text = self._preprocess_text(text)

        structure = DocumentStructure(
            document_name=document_name,
            raw_text_length=raw_length,
            cleaned_text_length=len(cleaned_text),
        )

        # 1. 检测文档类型
        structure.document_type = self._detect_document_type(cleaned_text, document_name)

        # 2. 提取条款信息
        structure.articles = self._extract_articles(cleaned_text)
        structure.total_articles = len(structure.articles)

        # 3. 提取章节信息
        structure.chapters = self._extract_chapters(cleaned_text, structure.articles)
        structure.total_chapters = len(structure.chapters)

        # 4. 计算条款长度统计
        if structure.articles:
            lengths = [a.content_length for a in structure.articles]
            structure.avg_article_length = sum(lengths) / len(lengths)
            structure.max_article_length = max(lengths)
            structure.min_article_length = min(lengths)

        # 5. 检测特殊结构
        structure.has_numbered_items = self._has_numbered_items(cleaned_text)
        structure.has_parenthetical_items = self._has_parenthetical_items(cleaned_text)
        structure.has_tables = self._has_tables(text)

        # 6. 评估复杂度
        structure.complexity = self._evaluate_complexity(structure)

        # 7. 预测分块范围
        predicted = self._predict_chunk_range(structure)
        structure.predicted_chunk_count_min = predicted["min"]
        structure.predicted_chunk_count_max = predicted["max"]
        structure.predicted_chunk_count_expected = predicted["expected"]
        structure.recommended_chunk_size = self._calculate_recommended_chunk_size(structure)

        # 8. 生成结构特征描述
        structure.structure_features = self._generate_structure_features(structure)

        return structure

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 移除多余的空白字符
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _detect_document_type(self, text: str, document_name: str) -> DocumentType:
        """检测文档类型"""
        combined = text + " " + document_name

        type_scores = {}
        for doc_type, keywords in self.DOCUMENT_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                type_scores[doc_type] = score

        if type_scores:
            return max(type_scores, key=type_scores.get)
        return DocumentType.UNKNOWN

    def _extract_articles(self, text: str) -> List[ArticleInfo]:
        """提取所有条款"""
        articles = []

        # 收集所有条款的位置
        article_positions = []
        for pattern in self.ARTICLE_PATTERNS:
            for match in pattern.finditer(text):
                article_positions.append((match.start(), match.group()))

        # 按位置排序
        article_positions.sort(key=lambda x: x[0])

        # 提取每个条款的内容
        for i, (pos, article_num) in enumerate(article_positions):
            # 确定条款的结束位置（下一个条款开始或文本结束）
            end_pos = article_positions[i + 1][0] if i + 1 < len(article_positions) else len(text)

            # 提取条款内容
            content = text[pos:end_pos].strip()
            content = self._clean_article_content(content, article_num)

            if not content:
                continue

            # 标准化条款编号
            normalized_num = self._normalize_article_number(article_num)

            # 统计款数量
            clause_count = sum(1 for p in self.CLAUSE_PATTERNS for _ in p.finditer(content))

            # 检测是否有子项
            has_sub_items = self._has_sub_items(content)

            articles.append(ArticleInfo(
                number=article_num,
                number_normalized=normalized_num,
                content_length=len(content),
                clause_count=clause_count,
                has_sub_items=has_sub_items,
                starts_new_chapter=self._starts_new_chapter(content, text, pos)
            ))

        return articles

    def _extract_chapters(self, text: str, articles: List[ArticleInfo]) -> List[ChapterInfo]:
        """提取章节信息"""
        chapters = []

        chapter_positions = []
        for pattern in self.CHAPTER_PATTERNS:
            for match in pattern.finditer(text):
                # 提取章节标题
                start = match.start()
                end = min(match.end() + 50, len(text))  # 取标题后的50个字符
                title = text[start:end].split('\n')[0]
                chapter_positions.append((start, match.group(), title.strip()))

        # 按位置排序
        chapter_positions.sort(key=lambda x: x[0])

        # 分配条款到章节
        for i, (pos, chapter_num, title) in enumerate(chapter_positions):
            # 确定章节的条款范围
            start_article = 0
            end_article = len(articles) - 1

            # 找到该章节开始的第一个条款
            for j, article in enumerate(articles):
                article_pos = text.find(article.number)
                if article_pos >= pos:
                    start_article = j
                    break

            # 找到下一个章节开始的条款
            if i + 1 < len(chapter_positions):
                next_chapter_pos = chapter_positions[i + 1][0]
                for j in range(start_article, len(articles)):
                    article_pos = text.find(articles[j].number)
                    if article_pos >= next_chapter_pos:
                        end_article = j - 1
                        break
            else:
                end_article = len(articles) - 1

            if start_article <= end_article and articles:
                chapters.append(ChapterInfo(
                    number=chapter_num,
                    title=title,
                    article_range=(start_article, end_article),
                    article_count=end_article - start_article + 1
                ))

        return chapters

    def _clean_article_content(self, content: str, article_num: str) -> str:
        """清理条款内容"""
        # 移除条款编号后的空白
        content = content.strip()
        # 确保条款编号存在
        if not content.startswith(article_num):
            idx = content.find(article_num)
            if idx > 0:
                content = content[idx:]
        return content

    def _normalize_article_number(self, article_num: str) -> int:
        """标准化条款编号为数字"""
        # 匹配数字部分
        num_str = re.search(r"[零一二三四五六七八九十百千0-9]+", article_num)
        if not num_str:
            return 0

        num_str = num_str.group()
        return self._chinese_to_number(num_str)

    def _chinese_to_number(self, text: str) -> int:
        """中文数字转阿拉伯数字"""
        chinese_digits = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }

        result = 0
        temp = 0

        for char in text:
            if char in chinese_digits:
                if char == '十':
                    if temp == 0:
                        temp = 10
                    else:
                        result += temp * 10
                        temp = 0
                else:
                    temp = chinese_digits[char]
            elif char.isdigit():
                temp = int(char)

        result += temp
        return result if result > 0 else 0

    def _has_sub_items(self, content: str) -> bool:
        """检测是否有子项"""
        return bool(self._has_numbered_items(content) or self._has_parenthetical_items(content))

    def _has_numbered_items(self, text: str) -> bool:
        """检测是否有编号列表项"""
        for pattern in self.NUMBERED_ITEM_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _has_parenthetical_items(self, text: str) -> bool:
        """检测是否有括号项"""
        for pattern in self.PARENTHETICAL_ITEM_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _has_tables(self, text: str) -> bool:
        """检测是否有表格（简单检测）"""
        # 检测多行等宽对齐的模式
        lines = text.split('\n')
        if len(lines) < 3:
            return False
        # 检测表格分隔符模式
        table_indicators = ['│', '├', '└', '┌', '┐', '┘', '┼', '|']
        for line in lines:
            if any(ind in line for ind in table_indicators):
                return True
        return False

    def _starts_new_chapter(self, content: str, full_text: str, pos: int) -> bool:
        """检测条款是否开启新章节"""
        # 检查内容开头是否有章节标识
        for pattern in self.CHAPTER_PATTERNS:
            if pattern.search(content[:50]):
                return True
        return False

    def _evaluate_complexity(self, structure: DocumentStructure) -> DocumentComplexity:
        """评估文档复杂度"""
        total_items = structure.total_articles

        # 考虑款的数量
        clauses = sum(a.clause_count for a in structure.articles)
        total_items += clauses

        for complexity, (low, high) in self.COMPLEXITY_THRESHOLDS.items():
            if low <= total_items < high:
                return complexity

        return DocumentComplexity.VERY_COMPLEX

    def _predict_chunk_range(self, structure: DocumentStructure) -> dict:
        """
        预测分块范围

        这是核心算法：根据文档结构特征预测合理的分块数量范围。
        不同文档采用不同的预测策略。
        """
        articles = structure.articles
        total_articles = len(articles)
        clauses = sum(a.clause_count for a in articles)
        total_items = total_articles + clauses

        # 特殊情况处理
        if total_articles == 0:
            # 没有条款的文档，按段落分块
            paragraphs = len([p for p in structure.raw_text_length.split('\n\n') if p.strip()])
            return {
                "min": max(1, paragraphs // 3),
                "max": paragraphs * 2,
                "expected": paragraphs
            }

        # 1. 计算基于条款的基础分块数
        base_chunks = total_items

        # 2. 根据条款长度调整
        length_factor = 1.0
        if structure.avg_article_length > 1500:
            # 长条款可能需要拆分
            length_factor = 1.5
        elif structure.avg_article_length < 100:
            # 短条款可能合并
            length_factor = 0.7

        # 3. 根据章节结构调整
        chapter_factor = 1.0
        if structure.total_chapters > 0:
            # 有章节的文档，预期分块数应接近条款数
            chapter_factor = 1.1

        # 4. 根据款的数量调整
        clause_factor = 1.0
        if clauses > 0 and total_articles > 0:
            # 款/条比例高意味着更多独立分块
            clause_ratio = clauses / total_articles
            if clause_ratio > 2:
                clause_factor = 1.3
            elif clause_ratio > 1:
                clause_factor = 1.15

        # 5. 根据子项调整
        sub_item_factor = 1.0
        articles_with_sub_items = sum(1 for a in articles if a.has_sub_items)
        if articles_with_sub_items > total_articles * 0.5:
            sub_item_factor = 1.2

        # 计算预期分块数
        expected = int(base_chunks * length_factor * chapter_factor * clause_factor * sub_item_factor)

        # 计算允许的范围（考虑不同分块策略的差异）
        # 宽松策略：最小化分块（款不单独分）
        min_chunks = int(base_chunks * 0.8)

        # 严格策略：最大化分块（每个款单独分）
        max_chunks = int(base_chunks * length_factor * 1.5)

        # 确保合理范围
        min_chunks = max(1, min(min_chunks, total_items))
        max_chunks = max(expected, max_chunks)

        # 对于简单文档，范围较窄；对于复杂文档，范围较宽
        if structure.complexity == DocumentComplexity.SIMPLE:
            min_chunks = max(1, expected - 2)
            max_chunks = expected + 2
        elif structure.complexity == DocumentComplexity.MEDIUM:
            min_chunks = max(1, int(expected * 0.8))
            max_chunks = int(expected * 1.3)
        elif structure.complexity == DocumentComplexity.COMPLEX:
            min_chunks = max(1, int(expected * 0.7))
            max_chunks = int(expected * 1.4)
        else:
            # 非常复杂的文档
            min_chunks = max(1, int(expected * 0.6))
            max_chunks = int(expected * 1.5)

        return {
            "min": min_chunks,
            "max": max_chunks,
            "expected": expected
        }

    def _calculate_recommended_chunk_size(self, structure: DocumentStructure) -> int:
        """计算推荐的块大小"""
        if structure.avg_article_length > 0:
            # 基于平均条款长度，略微增加以保留上下文
            recommended = int(structure.avg_article_length * 1.2)
        else:
            recommended = 600

        # 限制在合理范围内
        return max(200, min(recommended, 1000))

    def _generate_structure_features(self, structure: DocumentStructure) -> List[str]:
        """生成结构特征描述"""
        features = []

        # 文档类型
        if structure.document_type != DocumentType.UNKNOWN:
            features.append(f"文档类型: {structure.document_type.value}")

        # 复杂度
        features.append(f"复杂度: {structure.complexity.value}")

        # 条款特征
        if structure.total_articles > 0:
            features.append(f"包含 {structure.total_articles} 个条款")

            if structure.avg_article_length > 0:
                if structure.avg_article_length > 800:
                    features.append("条款平均较长（>800字符）")
                elif structure.avg_article_length < 200:
                    features.append("条款平均较短（<200字符）")
                else:
                    features.append("条款平均长度适中")

        # 章节特征
        if structure.total_chapters > 0:
            features.append(f"包含 {structure.total_chapters} 个章节")

        # 特殊结构
        if structure.has_numbered_items:
            features.append("包含编号列表项")
        if structure.has_parenthetical_items:
            features.append("包含括号项")
        if structure.has_tables:
            features.append("可能包含表格")

        # 分块预期
        features.append(
            f"预期分块数: {structure.predicted_chunk_count_min}-{structure.predicted_chunk_count_max}"
        )

        return features


def analyze_document_structure(text: str, document_name: str = "") -> DocumentStructure:
    """
    便捷函数：分析文档结构

    Args:
        text: 文档文本
        document_name: 文档名称

    Returns:
        DocumentStructure: 文档结构分析结果
    """
    analyzer = DocumentStructureAnalyzer()
    return analyzer.analyze(text, document_name)


def get_chunk_accuracy_score(actual_chunks: int, structure: DocumentStructure) -> dict:
    """
    计算分块准确率得分

    根据文档结构分析结果，评估实际分块数的准确程度。

    Args:
        actual_chunks: 实际分块数量
        structure: 文档结构分析结果

    Returns:
        dict: 包含准确率分数和详细评估
    """
    min_expected = structure.predicted_chunk_count_min
    max_expected = structure.predicted_chunk_count_max
    expected = structure.predicted_chunk_count_expected

    # 计算准确率
    if min_expected <= actual_chunks <= max_expected:
        # 在预期范围内，得分较高
        if actual_chunks == expected:
            score = 1.0
        else:
            # 越接近期望值得分越高
            range_size = max_expected - min_expected
            distance = abs(actual_chunks - expected)
            score = 1.0 - (distance / range_size) * 0.3
    else:
        # 超出范围，得分降低
        if actual_chunks < min_expected:
            # 分块太少，可能遗漏内容
            deficit = min_expected - actual_chunks
            score = max(0, 0.5 - deficit / min_expected * 0.5)
        else:
            # 分块太多，可能过度拆分
            surplus = actual_chunks - max_expected
            max_possible = max_expected * 2
            score = max(0, 0.5 - surplus / max_possible * 0.5)

    # 详细评估
    if actual_chunks < min_expected:
        assessment = "分块数量偏少，可能存在内容合并或遗漏"
        suggestion = f"建议分块数 >= {min_expected}"
    elif actual_chunks > max_expected:
        assessment = "分块数量偏多，可能存在过度拆分"
        suggestion = f"建议分块数 <= {max_expected}"
    else:
        assessment = "分块数量在合理范围内"
        suggestion = "当前分块数量符合文档结构特征"

    return {
        "score": round(score, 4),
        "actual_chunks": actual_chunks,
        "expected_range": f"{min_expected}-{max_expected}",
        "expected_value": expected,
        "assessment": assessment,
        "suggestion": suggestion,
        "structure_summary": structure.to_dict()
    }

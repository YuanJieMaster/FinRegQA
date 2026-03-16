"""
knowledge_base.py 的单元测试

说明：
- 使用 pytest
- 通过假数据库连接池 / 假游标 / 假嵌入模型 / 假 FAISS 索引进行隔离测试
- 不依赖真实 PostgreSQL、FAISS 和 SentenceTransformer 模型
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

import knowledge_base


# ===========================
# 假嵌入模型与假 FAISS 索引
# ===========================


class FakeEmbeddingModel:
    """简单的假嵌入模型：将文本长度映射为固定维度向量."""

    def __init__(self, dim: int = 8):
        self._dim = dim

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim

    def encode(
        self,
        sentences: List[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        embeddings: List[np.ndarray] = []
        for s in sentences:
            # 简单规则：第一个维度是长度，其余为 0
            vec = np.zeros(self._dim, dtype=np.float32)
            vec[0] = float(len(s))
            embeddings.append(vec)
        return np.stack(embeddings, axis=0)


class FakeIndexFlatL2:
    """简化版的 L2 距离索引."""

    def __init__(self, d: int):
        self.d = d
        self.vectors: List[np.ndarray] = []

    @property
    def ntotal(self) -> int:
        return len(self.vectors)

    def add(self, x: np.ndarray) -> None:
        for row in x:
            self.vectors.append(np.asarray(row, dtype=np.float32))

    def search(self, x: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        # 只支持单查询向量
        query = np.asarray(x[0], dtype=np.float32)
        if not self.vectors:
            return (
                np.full((1, k), np.inf, dtype=np.float32),
                np.full((1, k), -1, dtype=np.int64),
            )
        dists = [float(np.sum((v - query) ** 2)) for v in self.vectors]
        idxs = np.argsort(dists)[:k]
        top_dists = [dists[i] for i in idxs]
        # 填充到 k
        if len(idxs) < k:
            pad = k - len(idxs)
            idxs = np.concatenate([idxs, -1 * np.ones(pad, dtype=np.int64)])
            top_dists = top_dists + [np.inf] * pad
        return (
            np.asarray([top_dists], dtype=np.float32),
            np.asarray([idxs], dtype=np.int64),
        )


class FakeIndexIVFFlat(FakeIndexFlatL2):
    """模拟 IVF_FLAT，但内部直接复用 FlatL2 实现."""

    def __init__(self, quantizer: Any, d: int, nlist: int, metric: int):
        super().__init__(d)
        self.nlist = nlist
        self.is_trained = False

    def train(self, x: np.ndarray) -> None:
        # 简单标记为已训练
        self.is_trained = True


class FakeFaissModule:
    """提供与 knowledge_base 中使用到的 FAISS 接口兼容的假模块."""

    METRIC_L2 = 1

    IndexFlatL2 = FakeIndexFlatL2
    IndexIVFFlat = FakeIndexIVFFlat

    @staticmethod
    def read_index(path: str) -> FakeIndexIVFFlat:
        # 测试中不真正从磁盘读取，返回一个空索引即可
        # 维度在测试里不会走到 read_index 这条分支
        return FakeIndexIVFFlat(None, 8, 10, FakeFaissModule.METRIC_L2)

    @staticmethod
    def write_index(index: Any, path: str) -> None:
        # 测试中不真正写盘
        return None


# ===========================
# 假数据库实现
# ===========================


@dataclass
class FakeDocument:
    id: int
    name: str
    source: Optional[str]
    file_type: Optional[str]


@dataclass
class FakeKnowledge:
    id: int
    document_id: int
    content: str
    category: Optional[str]
    regulation_type: Optional[str]
    article_number: Optional[str]
    section_number: Optional[str]
    embedding_id: Optional[int] = None


@dataclass
class FakeLog:
    id: int
    operation: str
    knowledge_id: Optional[int]
    status: Optional[str]
    message: Optional[str]
    duration_ms: Optional[float]


@dataclass
class FakeDB:
    documents: Dict[int, FakeDocument] = field(default_factory=dict)
    knowledges: Dict[int, FakeKnowledge] = field(default_factory=dict)
    logs: List[FakeLog] = field(default_factory=list)
    next_doc_id: int = 1
    next_k_id: int = 1
    next_log_id: int = 1


class FakeCursor:
    def __init__(self, db: FakeDB):
        self.db = db
        self._last_fetchone: Optional[Tuple[Any, ...]] = None
        self._last_fetchall: List[Tuple[Any, ...]] = []

    # psycopg2 兼容 API
    def execute(self, query: str, params: Tuple[Any, ...] | None = None) -> None:
        q = " ".join(query.strip().split()).lower()
        params = params or ()

        # 文档插入
        if "insert into document" in q:
            name, source, file_type = params
            doc_id = self.db.next_doc_id
            self.db.next_doc_id += 1
            self.db.documents[doc_id] = FakeDocument(
                id=doc_id, name=name, source=source, file_type=file_type
            )
            self._last_fetchone = (doc_id,)

        # 知识点插入
        elif "insert into knowledge" in q:
            (
                document_id,
                content,
                category,
                regulation_type,
                article_number,
                section_number,
            ) = params
            k_id = self.db.next_k_id
            self.db.next_k_id += 1
            self.db.knowledges[k_id] = FakeKnowledge(
                id=k_id,
                document_id=document_id,
                content=content,
                category=category,
                regulation_type=regulation_type,
                article_number=article_number,
                section_number=section_number,
            )
            self._last_fetchone = (k_id,)

        # 更新 embedding_id
        elif "update knowledge set embedding_id" in q:
            embedding_id, k_id = params
            if k_id in self.db.knowledges:
                self.db.knowledges[k_id].embedding_id = int(embedding_id)

        # 日志插入
        elif "insert into log" in q:
            operation, knowledge_id, status, message, duration_ms = params
            log_id = self.db.next_log_id
            self.db.next_log_id += 1
            self.db.logs.append(
                FakeLog(
                    id=log_id,
                    operation=operation,
                    knowledge_id=knowledge_id,
                    status=status,
                    message=message,
                    duration_ms=duration_ms,
                )
            )

        # 统计 - 文档数
        elif q.startswith("select count(*) from document"):
            self._last_fetchone = (len(self.db.documents),)

        # 统计 - 知识点数
        elif q.startswith("select count(*) from knowledge"):
            self._last_fetchone = (len(self.db.knowledges),)

        # 分类统计
        elif "from knowledge" in q and "group by category" in q:
            stats: Dict[Optional[str], int] = {}
            for k in self.db.knowledges.values():
                if k.category is not None:
                    stats[k.category] = stats.get(k.category, 0) + 1
            self._last_fetchall = [(k, v) for k, v in stats.items()]

        # 监管类型统计
        elif "from knowledge" in q and "group by regulation_type" in q:
            stats: Dict[Optional[str], int] = {}
            for k in self.db.knowledges.values():
                if k.regulation_type is not None:
                    stats[k.regulation_type] = stats.get(k.regulation_type, 0) + 1
            self._last_fetchall = [(k, v) for k, v in stats.items()]

        # search 中的 SELECT ... JOIN ...
        elif "from knowledge k join document d" in q:
            (k_id,) = params
            k = self.db.knowledges.get(k_id)
            if not k:
                self._last_fetchone = None
            else:
                d = self.db.documents.get(k.document_id)
                self._last_fetchone = (
                    k.id,
                    k.content,
                    k.category,
                    k.regulation_type,
                    k.article_number,
                    k.section_number,
                    d.name if d else "",
                )

        # SAVEPOINT / ROLLBACK TO / RELEASE 等事务控制命令：在假实现中直接忽略
        elif q.startswith("savepoint") or q.startswith("rollback to") or q.startswith(
            "release savepoint"
        ):
            return

        # CREATE TABLE / CREATE INDEX 等初始化语句：在假实现中忽略
        elif q.startswith("create table") or q.startswith("create index"):
            return

        else:
            # 对于未覆盖的 SQL，在测试中直接忽略（也可以改为抛错帮助定位）
            return

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        return self._last_fetchone

    def fetchall(self) -> List[Tuple[Any, ...]]:
        return self._last_fetchall

    def close(self) -> None:
        return None


class FakeConnection:
    def __init__(self, db: FakeDB):
        self.db = db
        self.autocommit = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.db)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


class FakeConnectionPool:
    """模拟 psycopg2.pool.SimpleConnectionPool."""

    def __init__(self, minconn: int, maxconn: int, **kwargs: Any) -> None:
        self.db = FakeDB()

    def getconn(self) -> FakeConnection:
        return FakeConnection(self.db)

    def putconn(self, conn: FakeConnection) -> None:
        return None

    def closeall(self) -> None:
        return None


# ===========================
# Pytest fixtures
# ===========================


@pytest.fixture
def patched_kb(tmp_path, monkeypatch) -> knowledge_base.FinancialKnowledgeBase:
    """
    构造一个打好补丁的 FinancialKnowledgeBase 实例：
    - 使用假连接池
    - 使用假嵌入模型
    - 使用假 FAISS 模块
    - 将 FAISS 索引文件写入临时目录
    """

    # 1. 替换连接池
    monkeypatch.setattr(
        knowledge_base.psycopg2.pool,
        "SimpleConnectionPool",
        FakeConnectionPool,
    )

    # 2. 替换嵌入模型
    monkeypatch.setattr(
        knowledge_base,
        "SentenceTransformer",
        lambda model_name: FakeEmbeddingModel(dim=8),
    )

    # 3. 替换 FAISS 模块
    monkeypatch.setattr(knowledge_base, "faiss", FakeFaissModule)

    # 4. 创建实例
    kb = knowledge_base.FinancialKnowledgeBase(
        db_host="fake",
        db_port=5432,
        db_name="fake_db",
        db_user="user",
        db_password="pwd",
        embedding_model="fake-model",
        faiss_index_path=str(tmp_path / "faiss"),
        max_connections=5,
        embedding_dim=8,  # 与 FakeEmbeddingModel 一致
    )

    return kb


# ===========================
# 测试用例
# ===========================


def test_add_document_and_statistics(patched_kb: knowledge_base.FinancialKnowledgeBase):
    """测试 add_document 与 get_statistics 的基础行为."""
    kb = patched_kb

    # 初始统计
    stats0 = kb.get_statistics()
    assert stats0["document_count"] == 0
    assert stats0["knowledge_count"] == 0

    # 添加文档
    doc_id = kb.add_document(name="测试文档", source="unittest", file_type="txt")
    assert isinstance(doc_id, int)

    stats1 = kb.get_statistics()
    assert stats1["document_count"] == 1
    assert stats1["knowledge_count"] == 0


def test_add_knowledge_batch_and_search(patched_kb: knowledge_base.FinancialKnowledgeBase):
    """测试批量导入知识点与搜索功能."""
    kb = patched_kb

    # 创建一个文档
    doc_id = kb.add_document(name="测试文档", source="unittest", file_type="txt")

    items = [
        {
            "content": "第一条 为规范金融机构的经营行为，防范金融风险。",
            "category": "总则",
            "regulation_type": "风险管理",
            "article_number": "第一条",
            "section_number": "一",
        },
        {
            "content": "第二条 金融机构应当建立健全内部控制制度。",
            "category": "总则",
            "regulation_type": "内部控制",
            "article_number": "第二条",
            "section_number": "一",
        },
        {
            "content": "第三条 金融机构应当加强资本管理，保持充足的资本水平。",
            "category": "资本管理",
            "regulation_type": "资本管理",
            "article_number": "第三条",
            "section_number": "一",
        },
    ]

    success, failed = kb.add_knowledge_batch(document_id=doc_id, knowledge_items=items)
    assert success == len(items)
    assert failed == 0

    # knowledge_id_map 与 FAISS 索引数量应一致
    assert len(kb.knowledge_id_map) == len(items)
    assert int(kb.faiss_index.ntotal) == len(items)

    # 搜索一个已存在的语句，应当能命中
    query = "规范金融机构的经营行为"
    results = kb.search(query=query, top_k=3, threshold=0.001)

    assert len(results) >= 1
    # 相似度字段应存在且在 [0, 1] 范围内
    for r in results:
        assert 0.0 <= r["similarity"] <= 1.0
        assert "content" in r


def test_get_statistics_distribution(patched_kb: knowledge_base.FinancialKnowledgeBase):
    """测试 get_statistics 返回的分类与监管类型分布."""
    kb = patched_kb

    doc_id = kb.add_document(name="统计测试文档", source="unittest", file_type="txt")

    items = [
        {
            "content": "关于风险管理的第一条。",
            "category": "风险管理",
            "regulation_type": "风险管理",
            "article_number": "第一条",
            "section_number": "一",
        },
        {
            "content": "关于风险管理的第二条。",
            "category": "风险管理",
            "regulation_type": "风险管理",
            "article_number": "第二条",
            "section_number": "一",
        },
        {
            "content": "关于资本管理的条款。",
            "category": "资本管理",
            "regulation_type": "资本管理",
            "article_number": "第三条",
            "section_number": "一",
        },
    ]

    kb.add_knowledge_batch(document_id=doc_id, knowledge_items=items)

    stats = kb.get_statistics()

    assert stats["document_count"] == 1
    assert stats["knowledge_count"] == len(items)
    assert stats["faiss_index_size"] == len(items)

    # 分类分布
    cat_dist = stats["category_distribution"]
    assert cat_dist["风险管理"] == 2
    assert cat_dist["资本管理"] == 1

    # 监管类型分布
    reg_dist = stats["regulation_distribution"]
    assert reg_dist["风险管理"] == 2
    assert reg_dist["资本管理"] == 1


def test_close_does_not_raise(patched_kb: knowledge_base.FinancialKnowledgeBase):
    """简单测试 close 方法可正常调用."""
    kb = patched_kb
    # 不应抛出异常
    kb.close()


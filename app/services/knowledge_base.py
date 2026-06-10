"""
FinRegQA 金融知识库服务
Financial Knowledge Base Service - Using Milvus
"""
import os
import time
import logging
import re
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime
from functools import lru_cache

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from sqlalchemy.pool import QueuePool
import pymysql
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """金融知识库服务 - 使用 Milvus 向量数据库"""

    def __init__(
        self,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        milvus_user: str = "",
        milvus_password: str = "",
        collection_name: str = "financial_knowledge",
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        embedding_dim: int = 768,
        db_host: str = "localhost",
        db_port: int = 3306,
        db_name: str = "finregqa",
        db_user: str = "root",
        db_password: str = "root_password",
        db_pool_name: str = "finregqa_pool",
        db_pool_size: int = 10,
        db_pool_reset_session: bool = True,
        db_connect_timeout: int = 10,
        db_read_timeout: int = 30,
        db_write_timeout: int = 30,
    ):
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.milvus_user = milvus_user
        self.milvus_password = milvus_password
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_pool_name = db_pool_name
        self.db_pool_size = db_pool_size
        self.db_pool_reset_session = db_pool_reset_session
        self.db_connect_timeout = db_connect_timeout
        self.db_read_timeout = db_read_timeout
        self.db_write_timeout = db_write_timeout
        self._db_pool = self._create_db_pool()

        self._connect_milvus()

        logger.info(f"加载嵌入模型: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        try:
            model_dim = int(self.embedding_model.get_sentence_embedding_dimension())
            if model_dim != self.embedding_dim:
                logger.warning(f"检测到 embedding_dim={self.embedding_dim} 与模型维度={model_dim} 不一致，已自动使用模型维度")
                self.embedding_dim = model_dim
        except Exception as e:
            logger.warning(f"无法读取模型向量维度: {e}")

        self._init_collection()

    def _connect_milvus(self):
        """连接 Milvus 服务器"""
        alias = "default"
        try:
            connections.connect(
                alias=alias,
                host=self.milvus_host,
                port=self.milvus_port,
                user=self.milvus_user,
                password=self.milvus_password,
            )
            logger.info(f"Milvus 连接成功: {self.milvus_host}:{self.milvus_port}")
        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")
            raise

    def _init_collection(self):
        """初始化 Milvus Collection"""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)

            # 检查维度是否匹配
            schema = self.collection.schema
            embedding_field = next((f for f in schema.fields if f.name == "embedding"), None)
            if embedding_field and embedding_field.params.get("dim") != self.embedding_dim:
                logger.warning(f"Collection 向量维度不匹配: schema={embedding_field.params.get('dim')}, model={self.embedding_dim}")
                logger.info("删除旧 Collection 并重建...")
                utility.drop_collection(self.collection_name)
                self._create_collection()
            else:
                self.collection.load()
                logger.info(f"已加载现有 Collection: {self.collection_name}")
        else:
            self._create_collection()

    def _create_collection(self):
        """创建新的 Milvus Collection"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="knowledge_id", dtype=DataType.INT64, description="知识库ID"),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535, description="知识内容"),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=255, description="分类"),
            FieldSchema(name="region", dtype=DataType.VARCHAR, max_length=255, description="地区"),
            FieldSchema(name="regulation_type", dtype=DataType.VARCHAR, max_length=255, description="法规类型"),
            FieldSchema(name="article_number", dtype=DataType.VARCHAR, max_length=50, description="条款编号"),
            FieldSchema(name="section_number", dtype=DataType.VARCHAR, max_length=50, description="章节编号"),
            FieldSchema(name="document_id", dtype=DataType.INT64, description="文档ID"),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim, description="向量嵌入"),
        ]
        schema = CollectionSchema(fields=fields, description="金融知识库向量集合")
        self.collection = Collection(name=self.collection_name, schema=schema)
        logger.info(f"Collection 架构已创建, 向量维度: {self.embedding_dim}")

        # 使用 HNSW 图索引替换 IVF_FLAT
        index_params = {
            "metric_type": "L2",
            "index_type": "HNSW",
            "params": {
                "M": 16,               # 节点最大连接数，范围通常为 8~32
                "efConstruction": 200  # 索引构建时的搜索范围，越高构建越慢但精度越好
            }
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
        logger.info("HNSW 索引已创建，等待构建...")
        self.collection.load()
        logger.info(f"已创建并加载新 Collection: {self.collection_name}")

    def _create_db_pool(self):
        """Create a reusable MySQL connection pool for knowledge operations."""
        pool = QueuePool(
            creator=lambda: pymysql.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                charset="utf8mb4",
                autocommit=False,
                connect_timeout=self.db_connect_timeout,
                read_timeout=self.db_read_timeout,
                write_timeout=self.db_write_timeout,
            ),
            pool_size=self.db_pool_size,
            max_overflow=self.db_pool_size,
            recycle=3600,
            pre_ping=False,
            reset_on_return="rollback" if self.db_pool_reset_session else None,
        )
        logger.info(
            "MySQL connection pool initialized: %s@%s:%s/%s size=%s",
            self.db_user,
            self.db_host,
            self.db_port,
            self.db_name,
            self.db_pool_size,
        )
        return pool

    def _get_db_connection(self):
        """获取数据库连接"""
        return self._db_pool.connect()

    # ==================== 带缓存的向量提取方法 ====================
    @lru_cache(maxsize=2048)
    def _get_query_embedding(self, query: str) -> List[float]:
        """获取查询文本的向量表示（使用 LRU 缓存避免重复计算）"""
        return self.embedding_model.encode([query], convert_to_numpy=True)[0].tolist()
    # ========================================================================

    def add_document(self, name: str, source: str = None, file_type: str = None) -> int:
        """添加文档记录"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO document (name, source, file_type) VALUES (%s, %s, %s)",
                (name, source, file_type)
            )
            doc_id = cursor.lastrowid
            conn.commit()
            logger.info(f"文档添加成功: {name} (id={doc_id})")
            return doc_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"添加文档失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def add_knowledge_batch(
        self,
        document_id: int,
        knowledge_items: List[Dict],
        batch_size: int = 100
    ) -> Tuple[int, int]:
        """批量导入知识点"""
        start_time = time.time()
        success_count = 0
        fail_count = 0
        conn = None

        try:
            logger.info(f"开始批量导入 {len(knowledge_items)} 条知识点...")

            # 1. 先批量插入 MySQL，获取所有 knowledge_id
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 构建批量插入的 SQL
            insert_sql = """
                INSERT INTO knowledge
                (document_id, content, category, region, regulation_type, article_number, section_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            # 批量插入 MySQL
            values_list = [
                (
                    document_id,
                    item['content'],
                    item.get('category'),
                    item.get('region'),
                    item.get('regulation_type'),
                    item.get('article_number'),
                    item.get('section_number')
                )
                for item in knowledge_items
            ]

            cursor.executemany(insert_sql, values_list)
            conn.commit()

            # 获取插入的所有 ID
            cursor.execute("SELECT LAST_INSERT_ID()")
            first_id = cursor.fetchone()[0]
            knowledge_ids = list(range(first_id, first_id + len(knowledge_items)))
            logger.info(f"MySQL 插入完成, knowledge_ids: {first_id} ~ {first_id + len(knowledge_items) - 1}")

            # 2. 生成向量嵌入
            logger.info("开始生成向量嵌入...")
            contents = [item['content'] for item in knowledge_items]
            embeddings = self.embedding_model.encode(
                contents,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            embeddings_list = embeddings.tolist()
            logger.info(f"向量生成完成, 维度: {len(embeddings_list[0]) if embeddings_list else 0}")

            # 3. 批量插入 Milvus
            logger.info("开始批量插入 Milvus...")
            for batch_start in range(0, len(knowledge_items), batch_size):
                batch_end = min(batch_start + batch_size, len(knowledge_items))
                batch_items = knowledge_items[batch_start:batch_end]
                batch_ids = knowledge_ids[batch_start:batch_end]
                batch_embeddings = embeddings_list[batch_start:batch_end]

                # Milvus v2 需要按列组织数据
                entities = [
                    batch_ids,  # knowledge_id
                    [item['content'] or "" for item in batch_items],  # content
                    [item.get('category') or "" for item in batch_items],  # category
                    [item.get('region') or "" for item in batch_items],  # region
                    [item.get('regulation_type') or "" for item in batch_items],  # regulation_type
                    [item.get('article_number') or "" for item in batch_items],  # article_number
                    [item.get('section_number') or "" for item in batch_items],  # section_number
                    [document_id] * len(batch_items),  # document_id
                    batch_embeddings  # embedding
                ]

                try:
                    result = self.collection.insert(entities)
                    milvus_ids = result.primary_keys

                    # 更新 Milvus ID 到 MySQL
                    for kid, mvid in zip(batch_ids, milvus_ids):
                        cursor.execute(
                            "UPDATE knowledge SET milvus_id = %s WHERE id = %s",
                            (mvid, kid)
                        )
                    conn.commit()

                    # 刷新 Milvus 使数据立即可查询
                    self.collection.flush()

                    success_count += len(batch_items)
                    logger.info(f"批次 {batch_start}-{batch_end} 插入成功, {len(batch_items)} 条")

                except Exception as e:
                    logger.error(f"批次 {batch_start}-{batch_end} Milvus 插入失败: {e}")
                    fail_count += len(batch_items)

            duration = time.time() - start_time
            logger.info(f"批量导入完成: 成功{success_count}个, 失败{fail_count}个, 耗时{duration:.2f}秒")
            return success_count, fail_count

        except Exception as e:
            logger.error(f"批量导入失败: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
        region: Optional[str] = None,
        mode: str = "vector",
        return_analysis: bool = False,
    ) -> Union[List[Dict], Tuple[List[Dict], Dict]]:
        """检索知识点，支持耗时分析返回"""
        normalized_mode = (mode or "vector").strip().lower()
        if normalized_mode == "keyword":
            return self.keyword_search(query=query, top_k=top_k, region=region, return_analysis=return_analysis)
        if normalized_mode == "hybrid":
            return self.hybrid_search(
                query=query, top_k=top_k, threshold=threshold, region=region, return_analysis=return_analysis
            )
        if normalized_mode != "vector":
            raise ValueError("mode must be one of: vector, keyword, hybrid")

        start_time = time.time()
        analysis = {}
        try:
            # 1. 记录生成向量耗时
            t_emb_start = time.time()
            query_embedding = self._get_query_embedding(query)
            t_emb_end = time.time()
            analysis["embedding_time_ms"] = round((t_emb_end - t_emb_start) * 1000, 2)

            # 更新为 HNSW 对应的检索参数 ef
            ef_value = max(64, top_k * 2)
            search_params = {"metric_type": "L2", "params": {"ef": ef_value}}
            filter_expr = f'region == "{region}"' if region else None

            # 2. 记录 Milvus 检索耗时
            t_milvus_start = time.time()
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k * 2,
                output_fields=["knowledge_id", "content", "category", "region",
                             "regulation_type", "article_number", "section_number", "document_id"],
                expr=filter_expr
            )
            t_milvus_end = time.time()
            analysis["milvus_search_time_ms"] = round((t_milvus_end - t_milvus_start) * 1000, 2)

            # 3. 记录 MySQL 查询耗时
            t_mysql_start = time.time()
            search_results = []
            conn = None
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()

                for hits in results:
                    for hit in hits:
                        distance = hit.distance
                        similarity = 1.0 / (1.0 + distance)

                        if similarity >= threshold:
                            knowledge_id = hit.entity.get("knowledge_id")
                            search_results.append({
                                'knowledge_id': knowledge_id,
                                'content': hit.entity.get("content"),
                                'category': hit.entity.get("category"),
                                'region': hit.entity.get("region"),
                                'regulation_type': hit.entity.get("regulation_type"),
                                'article_number': hit.entity.get("article_number"),
                                'section_number': hit.entity.get("section_number"),
                                'document_name': "",
                                'similarity': float(similarity),
                                'distance': float(distance),
                                'vector_score': float(similarity),
                                'search_mode': 'vector',
                            })

                search_results = search_results[:top_k]
                knowledge_ids = [item["knowledge_id"] for item in search_results if item.get("knowledge_id") is not None]

                if knowledge_ids:
                    placeholders = ", ".join(["%s"] * len(knowledge_ids))
                    cursor.execute(
                        f"""
                            SELECT k.id, d.name
                            FROM knowledge k
                            JOIN document d ON k.document_id = d.id
                            WHERE k.id IN ({placeholders})
                        """,
                        tuple(knowledge_ids),
                    )
                    document_name_map = {row[0]: row[1] for row in cursor.fetchall()}
                    for item in search_results:
                        item["document_name"] = document_name_map.get(item["knowledge_id"], "")

                t_mysql_end = time.time()
                analysis["mysql_lookup_time_ms"] = round((t_mysql_end - t_mysql_start) * 1000, 2)

                # 计算总耗时
                total_duration = time.time() - start_time
                analysis["total_time_ms"] = round(total_duration * 1000, 2)

                print(f"\n{'=' * 60}")
                print(f"查询耗时分析:")
                print(f"  向量生成: {analysis.get('embedding_time_ms', 0)}ms")
                print(f"  Milvus检索: {analysis.get('milvus_search_time_ms', 0)}ms")
                print(f"  MySQL查询: {analysis.get('mysql_lookup_time_ms', 0)}ms")
                print(f"  总耗时: {analysis.get('total_time_ms', 0)}ms")
                print(f"{'=' * 60}\n")

                log_msg = f"查询: {query}, 结果数: {len(search_results)} | 耗时分析: {json.dumps(analysis, ensure_ascii=False)}"
                self._log_operation('search', 'success', log_msg, total_duration * 1000)
                logger.info(f"检索完成: {len(search_results)}个结果, 耗时{total_duration:.3f}秒. 详情: {analysis}")

                if total_duration > 2.0:
                    logger.warning(f"检索响应时间超过2秒: {total_duration:.3f}秒")

                if return_analysis:
                    return search_results, analysis
                return search_results
            finally:
                if conn:
                    conn.close()
        except Exception as e:
            logger.error(f"检索失败: {e}")
            raise

    def keyword_search(
        self,
        query: str,
        top_k: int = 5,
        region: Optional[str] = None,
        return_analysis: bool = False,
    ) -> Union[List[Dict], Tuple[List[Dict], Dict]]:
        """Search knowledge items by pure keyword matching."""
        start_time = time.time()
        analysis = {}

        q = (query or "").strip()
        if not q:
            if return_analysis:
                return [], {"total_time_ms": 0}
            return []

        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            t_mysql_start = time.time()
            try:
                results = self._keyword_search_fulltext(cursor, q, top_k, region)
                analysis["search_type"] = "fulltext"
            except Exception as e:
                logger.warning("FULLTEXT keyword search failed, fallback to LIKE: %s", e)
                results = self._keyword_search_like(cursor, q, top_k, region)
                analysis["search_type"] = "like_fallback"
            t_mysql_end = time.time()

            analysis["mysql_search_time_ms"] = round((t_mysql_end - t_mysql_start) * 1000, 2)
            total_duration = time.time() - start_time
            analysis["total_time_ms"] = round(total_duration * 1000, 2)

            log_msg = f"query: {q}, results: {len(results)} | 耗时分析: {json.dumps(analysis, ensure_ascii=False)}"
            self._log_operation('keyword_search', 'success', log_msg, total_duration * 1000)
            logger.info("Keyword search finished: %s results, %.3fs", len(results), total_duration)

            if return_analysis:
                return results, analysis
            return results
        except Exception as e:
            logger.error("Keyword search failed: %s", e)
            raise
        finally:
            if conn:
                conn.close()

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
        region: Optional[str] = None,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
        return_analysis: bool = False,
    ) -> Union[List[Dict], Tuple[List[Dict], Dict]]:
        """Fuse vector and keyword results with reciprocal-rank fusion."""
        t_start = time.time()
        analysis = {}

        # 执行向量检索并获取耗时
        vector_results, vector_analysis = self.search(
            query=query, top_k=max(top_k * 3, top_k), threshold=threshold,
            region=region, mode="vector", return_analysis=True
        )

        # 执行关键词检索并获取耗时
        keyword_results, keyword_analysis = self.keyword_search(
            query=query, top_k=max(top_k * 3, top_k), region=region, return_analysis=True
        )

        t_fusion_start = time.time()
        fused: Dict[int, Dict] = {}
        rrf_k = 60.0

        def add_results(results: List[Dict], source: str, weight: float) -> None:
            for rank, item in enumerate(results, 1):
                knowledge_id = item.get("knowledge_id")
                if knowledge_id is None:
                    continue

                score = weight / (rrf_k + rank)
                if knowledge_id not in fused:
                    merged = dict(item)
                    merged["hybrid_score"] = 0.0
                    merged["vector_score"] = 0.0
                    merged["keyword_score"] = 0.0
                    merged["search_mode"] = "hybrid"
                    fused[knowledge_id] = merged

                fused_item = fused[knowledge_id]
                fused_item["hybrid_score"] += score
                if source == "vector":
                    fused_item["vector_score"] = max(
                        float(fused_item.get("vector_score") or 0.0),
                        float(item.get("vector_score") or item.get("similarity") or 0.0),
                    )
                else:
                    fused_item["keyword_score"] = max(
                        float(fused_item.get("keyword_score") or 0.0),
                        float(item.get("keyword_score") or item.get("similarity") or 0.0),
                    )

        add_results(vector_results, "vector", vector_weight)
        add_results(keyword_results, "keyword", keyword_weight)

        results = sorted(
            fused.values(),
            key=lambda item: (
                float(item.get("hybrid_score") or 0.0),
                float(item.get("vector_score") or 0.0),
                float(item.get("keyword_score") or 0.0),
            ),
            reverse=True,
        )[:top_k]

        max_score = max((float(item.get("hybrid_score") or 0.0) for item in results), default=0.0)
        if max_score > 0:
            for item in results:
                item["similarity"] = float(item.get("hybrid_score") or 0.0) / max_score

        t_fusion_end = time.time()

        # 组装完整的统计分析数据
        analysis["vector_search_total_ms"] = vector_analysis.get("total_time_ms", 0)
        analysis["keyword_search_total_ms"] = keyword_analysis.get("total_time_ms", 0)
        analysis["fusion_time_ms"] = round((t_fusion_end - t_fusion_start) * 1000, 2)
        analysis["total_time_ms"] = round((time.time() - t_start) * 1000, 2)
        analysis["detailed_breakdown"] = {
            "vector_details": vector_analysis,
            "keyword_details": keyword_analysis
        }

        if return_analysis:
            return results, analysis
        return results

    def _keyword_search_fulltext(
        self,
        cursor,
        query: str,
        top_k: int,
        region: Optional[str],
    ) -> List[Dict]:
        score_expr = """
            MATCH(k.content, k.category, k.regulation_type, k.article_number, k.section_number)
            AGAINST (%s IN NATURAL LANGUAGE MODE)
        """
        where = [f"{score_expr} > 0"]
        params = [query, query]
        if region:
            where.append("k.region = %s")
            params.append(region)
        params.append(top_k)

        sql = f"""
            SELECT
                k.id,
                k.content,
                k.category,
                k.region,
                k.regulation_type,
                k.article_number,
                k.section_number,
                d.name AS document_name,
                {score_expr} AS keyword_score
            FROM knowledge k
            JOIN document d ON k.document_id = d.id
            WHERE {' AND '.join(where)}
            ORDER BY keyword_score DESC, k.id DESC
            LIMIT %s
        """
        cursor.execute(sql, tuple(params))
        return self._format_keyword_rows(cursor.fetchall())

    def _keyword_search_like(
        self,
        cursor,
        query: str,
        top_k: int,
        region: Optional[str],
    ) -> List[Dict]:
        terms = self._extract_keyword_terms(query)
        searchable_columns = [
            ("k.content", 3),
            ("k.category", 2),
            ("k.regulation_type", 2),
            ("k.article_number", 1),
            ("k.section_number", 1),
        ]

        score_parts = []
        score_params = []
        where_parts = []
        where_params = []
        for term in terms:
            like = f"%{term}%"
            term_matches = []
            for column, weight in searchable_columns:
                score_parts.append(f"CASE WHEN {column} LIKE %s THEN {weight} ELSE 0 END")
                score_params.append(like)
                term_matches.append(f"{column} LIKE %s")
                where_params.append(like)
            where_parts.append("(" + " OR ".join(term_matches) + ")")

        where = where_parts or ["k.content LIKE %s"]
        if not where_parts:
            where_params.append(f"%{query}%")
        if region:
            where.append("k.region = %s")
            where_params.append(region)

        score_expr = " + ".join(score_parts) if score_parts else "1"
        sql = f"""
            SELECT
                k.id,
                k.content,
                k.category,
                k.region,
                k.regulation_type,
                k.article_number,
                k.section_number,
                d.name AS document_name,
                ({score_expr}) AS keyword_score
            FROM knowledge k
            JOIN document d ON k.document_id = d.id
            WHERE {' AND '.join(where)}
            ORDER BY keyword_score DESC, k.id DESC
            LIMIT %s
        """
        cursor.execute(sql, tuple(score_params + where_params + [top_k]))
        return self._format_keyword_rows(cursor.fetchall())

    def _extract_keyword_terms(self, query: str) -> List[str]:
        terms = re.findall(r"[\w\u4e00-\u9fff]+", query or "", flags=re.UNICODE)
        if not terms and query:
            terms = [query]
        return list(dict.fromkeys(term for term in terms if term.strip()))

    def _format_keyword_rows(self, rows) -> List[Dict]:
        results = []
        for row in rows:
            keyword_score = float(row[8] or 0.0)
            results.append({
                'knowledge_id': row[0],
                'content': row[1],
                'category': row[2],
                'region': row[3],
                'regulation_type': row[4],
                'article_number': row[5],
                'section_number': row[6],
                'document_name': row[7] or "",
                'similarity': keyword_score / (keyword_score + 1.0) if keyword_score > 0 else 0.0,
                'keyword_score': keyword_score,
                'search_mode': 'keyword',
            })
        return results

    def _log_operation(self, operation: str, status: str = None, message: str = None,
                      duration_ms: float = None, knowledge_id: int = None):
        """记录操作日志"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO log (operation, knowledge_id, status, message, duration_ms) VALUES (%s, %s, %s, %s, %s)",
                (operation, knowledge_id, status, message, duration_ms)
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"记录日志失败: {e}")
        finally:
            if conn:
                conn.close()

    def get_statistics(self) -> Dict:
        """获取知识库统计信息"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM document")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge")
            knowledge_count = cursor.fetchone()[0]

            milvus_count = self.collection.num_entities

            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM knowledge
                WHERE category IS NOT NULL
                GROUP BY category
            """)
            category_stats = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT regulation_type, COUNT(*) as count
                FROM knowledge
                WHERE regulation_type IS NOT NULL
                GROUP BY regulation_type
            """)
            regulation_stats = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT region, COUNT(*) as count
                FROM knowledge
                WHERE region IS NOT NULL
                GROUP BY region
            """)
            region_stats = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                'document_count': doc_count,
                'knowledge_count': knowledge_count,
                'milvus_vector_count': milvus_count,
                'category_distribution': category_stats,
                'regulation_distribution': regulation_stats,
                'region_distribution': region_stats
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_all_knowledge(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        region: Optional[str] = None,
        regulation_type: Optional[str] = None,
        search_keyword: Optional[str] = None,
    ) -> Tuple[List[Dict], int]:
        """获取所有知识点（支持分页和筛选）"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            where_clauses = []
            params = []

            if category:
                where_clauses.append("k.category = %s")
                params.append(category)
            if region:
                where_clauses.append("k.region = %s")
                params.append(region)
            if regulation_type:
                where_clauses.append("k.regulation_type = %s")
                params.append(regulation_type)
            if search_keyword:
                where_clauses.append("(k.content LIKE %s OR k.article_number LIKE %s)")
                like_pattern = f"%{search_keyword}%"
                params.extend([like_pattern, like_pattern])

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 获取总数
            count_sql = f"""
                SELECT COUNT(*)
                FROM knowledge k
                WHERE {where_sql}
            """
            cursor.execute(count_sql, tuple(params))
            total = cursor.fetchone()[0]

            # 获取分页数据
            query_sql = f"""
                SELECT k.id, k.document_id, k.content, k.category, k.region,
                       k.regulation_type, k.article_number, k.section_number,
                       k.milvus_id, k.created_at, k.updated_at, d.name as document_name
                FROM knowledge k
                LEFT JOIN document d ON k.document_id = d.id
                WHERE {where_sql}
                ORDER BY k.updated_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query_sql, tuple(params + [limit, skip]))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'document_id': row[1],
                    'content': row[2],
                    'category': row[3],
                    'region': row[4],
                    'regulation_type': row[5],
                    'article_number': row[6],
                    'section_number': row[7],
                    'milvus_id': row[8],
                    'created_at': str(row[9]) if row[9] else None,
                    'updated_at': str(row[10]) if row[10] else None,
                    'document_name': row[11],
                })

            return results, total

        except Exception as e:
            logger.error(f"获取知识点列表失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_knowledge_by_id(self, knowledge_id: int) -> Optional[Dict]:
        """根据ID获取单个知识点"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            sql = """
                SELECT k.id, k.document_id, k.content, k.category, k.region,
                       k.regulation_type, k.article_number, k.section_number,
                       k.milvus_id, k.created_at, k.updated_at, d.name as document_name
                FROM knowledge k
                LEFT JOIN document d ON k.document_id = d.id
                WHERE k.id = %s
            """
            cursor.execute(sql, (knowledge_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                'id': row[0],
                'document_id': row[1],
                'content': row[2],
                'category': row[3],
                'region': row[4],
                'regulation_type': row[5],
                'article_number': row[6],
                'section_number': row[7],
                'milvus_id': row[8],
                'created_at': str(row[9]) if row[9] else None,
                'updated_at': str(row[10]) if row[10] else None,
                'document_name': row[11],
            }

        except Exception as e:
            logger.error(f"获取知识点失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_knowledge(
        self,
        knowledge_id: int,
        content: Optional[str] = None,
        category: Optional[str] = None,
        region: Optional[str] = None,
        regulation_type: Optional[str] = None,
        article_number: Optional[str] = None,
        section_number: Optional[str] = None,
    ) -> bool:
        """更新知识点"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            update_fields = []
            params = []

            if content is not None:
                update_fields.append("content = %s")
                params.append(content)
            if category is not None:
                update_fields.append("category = %s")
                params.append(category)
            if region is not None:
                update_fields.append("region = %s")
                params.append(region)
            if regulation_type is not None:
                update_fields.append("regulation_type = %s")
                params.append(regulation_type)
            if article_number is not None:
                update_fields.append("article_number = %s")
                params.append(article_number)
            if section_number is not None:
                update_fields.append("section_number = %s")
                params.append(section_number)

            if not update_fields:
                return False

            update_fields.append("updated_at = NOW()")
            params.append(knowledge_id)

            sql = f"""
                UPDATE knowledge
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            cursor.execute(sql, tuple(params))
            conn.commit()

            # 如果内容更新了，也需要更新 Milvus 中的向量
            if content is not None:
                self._update_milvus_vector(knowledge_id, content)

            logger.info(f"知识点更新成功: id={knowledge_id}")
            return cursor.rowcount > 0

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"更新知识点失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _update_milvus_vector(self, knowledge_id: int, new_content: str):
        """更新 Milvus 中的向量"""
        try:
            # 获取旧的 Milvus ID
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT milvus_id, document_id FROM knowledge WHERE id = %s", (knowledge_id,))
            row = cursor.fetchone()
            if not row or not row[0]:
                conn.close()
                return
            milvus_id = row[0]
            document_id = row[1]
            conn.close()

            # 生成新的向量 (使用缓存)
            embedding = self._get_query_embedding(new_content)

            # 删除旧的向量
            delete_expr = f"knowledge_id == {knowledge_id}"
            self.collection.delete(delete_expr)

            # 插入新的向量
            cursor = conn.cursor() if conn else None
            entities = [
                [knowledge_id],
                [new_content],
                [""],  # category
                [""],  # region
                [""],  # regulation_type
                [""],  # article_number
                [""],  # section_number
                [document_id],
                [embedding],
            ]
            result = self.collection.insert(entities)
            new_milvus_id = result.primary_keys[0]

            # 更新 MySQL 中的 milvus_id
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE knowledge SET milvus_id = %s WHERE id = %s", (new_milvus_id, knowledge_id))
            conn.commit()
            conn.close()

            self.collection.flush()
            logger.info(f"Milvus 向量更新成功: knowledge_id={knowledge_id}")

        except Exception as e:
            logger.error(f"更新 Milvus 向量失败: {e}")

    def delete_knowledge(self, knowledge_id: int) -> bool:
        """删除知识点（同时删除 MySQL 和 Milvus 中的记录）"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 获取 Milvus ID
            cursor.execute("SELECT milvus_id FROM knowledge WHERE id = %s", (knowledge_id,))
            row = cursor.fetchone()

            if not row:
                return False

            milvus_id = row[0]

            # 删除 MySQL 记录
            cursor.execute("DELETE FROM knowledge WHERE id = %s", (knowledge_id,))
            conn.commit()

            # 删除 Milvus 向量
            if milvus_id:
                try:
                    delete_expr = f"knowledge_id == {knowledge_id}"
                    self.collection.delete(delete_expr)
                    self.collection.flush()
                except Exception as e:
                    logger.warning(f"删除 Milvus 向量失败（已删除 MySQL 记录）: {e}")

            logger.info(f"知识点删除成功: id={knowledge_id}")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"删除知识点失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_all_documents(self) -> List[Dict]:
        """获取所有文档列表"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            sql = """
                SELECT d.id, d.name, d.source, d.file_type, d.created_at, d.updated_at,
                       COUNT(k.id) as knowledge_count
                FROM document d
                LEFT JOIN knowledge k ON d.id = k.document_id
                GROUP BY d.id
                ORDER BY d.updated_at DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'name': row[1],
                    'source': row[2],
                    'file_type': row[3],
                    'created_at': str(row[4]) if row[4] else None,
                    'updated_at': str(row[5]) if row[5] else None,
                    'knowledge_count': row[6],
                })

            return results

        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def delete_document(self, document_id: int) -> bool:
        """删除文档及其所有知识点"""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 先获取所有相关的 milvus_id
            cursor.execute("SELECT milvus_id FROM knowledge WHERE document_id = %s", (document_id,))
            milvus_ids = [row[0] for row in cursor.fetchall() if row[0]]

            # 删除 MySQL 中的知识点和文档
            cursor.execute("DELETE FROM knowledge WHERE document_id = %s", (document_id,))
            cursor.execute("DELETE FROM document WHERE id = %s", (document_id,))
            conn.commit()

            # 删除 Milvus 向量
            if milvus_ids:
                try:
                    for mid in milvus_ids:
                        delete_expr = f"knowledge_id in {[mid]}"
                        self.collection.delete(delete_expr)
                    self.collection.flush()
                except Exception as e:
                    logger.warning(f"删除 Milvus 向量失败: {e}")

            logger.info(f"文档删除成功: id={document_id}")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"删除文档失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_distinct_values(self, field: str) -> List[str]:
        """获取某字段的所有不重复值"""
        conn = None
        allowed_fields = ['category', 'region', 'regulation_type']
        if field not in allowed_fields:
            raise ValueError(f"field must be one of: {allowed_fields}")

        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT DISTINCT {field} FROM knowledge WHERE {field} IS NOT NULL AND {field} != '' ORDER BY {field}")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取字段值失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def close(self):
        """关闭连接"""
        try:
            connections.disconnect("default")
            logger.info("Milvus 连接已关闭")
        except Exception as e:
            logger.warning(f"关闭 Milvus 连接时出错: {e}")


_default_kb = None

def get_default_kb() -> KnowledgeBaseService:
    """获取默认知识库实例"""
    global _default_kb
    if _default_kb is None:
        settings = get_settings()
        _default_kb = KnowledgeBaseService(
            milvus_host=settings.MILVUS_HOST,
            milvus_port=settings.MILVUS_PORT,
            milvus_user=settings.MILVUS_USER,
            milvus_password=settings.MILVUS_PASSWORD,
            collection_name=settings.MILVUS_COLLECTION,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dim=settings.EMBEDDING_DIM,
            db_host=settings.MYSQL_HOST,
            db_port=settings.MYSQL_PORT,
            db_name=settings.MYSQL_DATABASE,
            db_user=settings.MYSQL_USER,
            db_password=settings.MYSQL_PASSWORD,
            db_pool_name=settings.MYSQL_POOL_NAME,
            db_pool_size=settings.MYSQL_POOL_SIZE,
            db_pool_reset_session=settings.MYSQL_POOL_RESET_SESSION,
            db_connect_timeout=settings.MYSQL_CONNECT_TIMEOUT,
            db_read_timeout=settings.MYSQL_READ_TIMEOUT,
            db_write_timeout=settings.MYSQL_WRITE_TIMEOUT,
        )
    return _default_kb

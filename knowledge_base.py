"""
PostgreSQL + FAISS 金融知识库系统
Financial Knowledge Base with PostgreSQL + FAISS

功能：
1. PostgreSQL表设计（document/knowledge/log）
2. FAISS向量索引（IVF_FLAT，dim=768）
3. 批量导入金融知识点
4. 连接异常处理和索引优化
5. 检索响应时间控制（≤2秒）
"""

import os
import time
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import json

import psycopg2
from psycopg2 import pool, sql, Error as PgError
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinancialKnowledgeBase:
    """
    金融知识库系统
    
    集成PostgreSQL存储元数据和FAISS向量检索
    """
    
    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 5432,
        db_name: str = "financial_kb",
        db_user: str = "postgres",
        db_password: str = "postgres",
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        faiss_index_path: str = "./faiss_index",
        max_connections: int = 10,
        embedding_dim: int = 768
    ):
        """
        初始化知识库
        
        Args:
            db_host: PostgreSQL主机
            db_port: PostgreSQL端口
            db_name: 数据库名称
            db_user: 数据库用户
            db_password: 数据库密码
            embedding_model: 嵌入模型名称
            faiss_index_path: FAISS索引保存路径
            max_connections: 最大连接数
            embedding_dim: 嵌入向量维度
        """
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.embedding_model_name = embedding_model
        self.faiss_index_path = faiss_index_path
        self.embedding_dim = embedding_dim
        
        # 初始化连接池
        self.connection_pool = None
        self._init_connection_pool(max_connections)
        
        # 初始化嵌入模型
        logger.info(f"加载嵌入模型: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # 以模型实际输出维度为准，避免 FAISS 维度不匹配
        try:
            model_dim = int(self.embedding_model.get_sentence_embedding_dimension())
            if model_dim != self.embedding_dim:
                logger.warning(
                    "检测到 embedding_dim=%s 与模型维度=%s 不一致，已自动使用模型维度",
                    self.embedding_dim,
                    model_dim,
                )
                self.embedding_dim = model_dim
        except Exception as e:
            logger.warning("无法读取模型向量维度，将继续使用 embedding_dim=%s: %s", self.embedding_dim, e)
        
        # 初始化FAISS索引
        self.faiss_index = None
        self.knowledge_id_map = {}  # knowledge_id -> faiss_index_id映射
        self._init_faiss_index()
        
        # 初始化数据库表
        self._init_database()
    
    def _init_connection_pool(self, max_connections: int):
        """初始化PostgreSQL连接池"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,
                max_connections,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                connect_timeout=5
            )
            logger.info(f"PostgreSQL连接池初始化成功 (最大连接数: {max_connections})")
        except PgError as e:
            logger.error(f"连接池初始化失败: {e}")
            raise
    
    def _get_connection(self):
        """从连接池获取连接"""
        try:
            conn = self.connection_pool.getconn()
            conn.autocommit = False
            return conn
        except pool.PoolError as e:
            logger.error(f"获取连接失败: {e}")
            raise
    
    def _return_connection(self, conn):
        """归还连接到连接池"""
        if conn:
            self.connection_pool.putconn(conn)
    
    def _init_faiss_index(self):
        """初始化FAISS索引"""
        os.makedirs(self.faiss_index_path, exist_ok=True)
        index_file = os.path.join(self.faiss_index_path, "financial_kb.index")
        id_map_file = os.path.join(self.faiss_index_path, "id_map.json")
        
        if os.path.exists(index_file) and os.path.exists(id_map_file):
            # 加载现有索引
            logger.info("加载现有FAISS索引")
            loaded_index = faiss.read_index(index_file)
            if getattr(loaded_index, "d", None) != self.embedding_dim:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_index = os.path.join(self.faiss_index_path, f"financial_kb.index.bak_{ts}")
                backup_map = os.path.join(self.faiss_index_path, f"id_map.json.bak_{ts}")
                logger.warning(
                    "检测到现有FAISS索引维度=%s 与当前 embedding_dim=%s 不一致，已备份并重建索引",
                    getattr(loaded_index, "d", None),
                    self.embedding_dim,
                )
                try:
                    os.replace(index_file, backup_index)
                    os.replace(id_map_file, backup_map)
                except Exception as e:
                    logger.warning("备份旧索引文件失败，将直接重建新索引: %s", e)
                self.faiss_index = None
                self.knowledge_id_map = {}
            else:
                self.faiss_index = loaded_index
                with open(id_map_file, 'r') as f:
                    self.knowledge_id_map = json.load(f)
        else:
            # 创建新索引：IVF_FLAT
            logger.info(f"创建新FAISS索引 (dim={self.embedding_dim}, IVF_FLAT)")
            quantizer = faiss.IndexFlatL2(self.embedding_dim)
            nlist = 10  # 聚类中心数量
            self.faiss_index = faiss.IndexIVFFlat(
                quantizer,
                self.embedding_dim,
                nlist,
                faiss.METRIC_L2
            )
            self.knowledge_id_map = {}

        if self.faiss_index is None:
            logger.info(f"创建新FAISS索引 (dim={self.embedding_dim}, IVF_FLAT)")
            quantizer = faiss.IndexFlatL2(self.embedding_dim)
            nlist = 10
            self.faiss_index = faiss.IndexIVFFlat(
                quantizer,
                self.embedding_dim,
                nlist,
                faiss.METRIC_L2
            )
            self.knowledge_id_map = {}

        self.faiss_index.nprobe = 10
        # print("FAISS 索引里总向量数量：", self.faiss_index.ntotal)
    
    def _init_database(self):
        """初始化PostgreSQL数据库表"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 创建document表（文档元数据）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    source VARCHAR(255),
                    file_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建knowledge表（知识点）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    category VARCHAR(100),
                    regulation_type VARCHAR(100),
                    article_number VARCHAR(50),
                    section_number VARCHAR(50),
                    embedding_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建log表（操作日志）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log (
                    id SERIAL PRIMARY KEY,
                    operation VARCHAR(50) NOT NULL,
                    knowledge_id INTEGER REFERENCES knowledge(id) ON DELETE SET NULL,
                    status VARCHAR(20),
                    message TEXT,
                    duration_ms FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引以优化查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_document_id 
                ON knowledge(document_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_category 
                ON knowledge(category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_article 
                ON knowledge(article_number)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_operation 
                ON log(operation)
            """)
            
            conn.commit()
            logger.info("数据库表初始化成功")
        
        except PgError as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库初始化失败: {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def add_document(self, name: str, source: str = None, file_type: str = None) -> int:
        """
        添加文档记录
        
        Args:
            name: 文档名称
            source: 文档来源
            file_type: 文件类型
            
        Returns:
            document_id
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO document (name, source, file_type)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (name, source, file_type))
            
            doc_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"文档添加成功: {name} (id={doc_id})")
            return doc_id
        
        except PgError as e:
            if conn:
                conn.rollback()
            logger.error(f"添加文档失败: {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def add_knowledge_batch(
        self,
        document_id: int,
        knowledge_items: List[Dict],
        batch_size: int = 100
    ) -> Tuple[int, int]:
        """
        批量导入知识点
        
        Args:
            document_id: 文档ID
            knowledge_items: 知识点列表，每项包含：
                - content: 知识点内容（必需）
                - category: 分类（可选）
                - regulation_type: 监管类型（可选）
                - article_number: 条款号（可选）
                - section_number: 款号（可选）
            batch_size: 批处理大小
            
        Returns:
            (成功数, 失败数)
        """
        start_time = time.time()
        success_count = 0
        fail_count = 0
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 生成嵌入向量
            logger.info(f"生成{len(knowledge_items)}个知识点的嵌入向量")
            contents = [item['content'] for item in knowledge_items]
            embeddings = self.embedding_model.encode(
                contents,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True
            )

            # IVF 类索引在 add 之前必须先 train
            embeddings_f32 = embeddings.astype(np.float32, copy=False)
            if embeddings_f32.ndim != 2 or embeddings_f32.shape[1] != self.embedding_dim:
                raise ValueError(
                    f"嵌入向量维度不匹配: embeddings.shape={embeddings_f32.shape}, expected_dim={self.embedding_dim}"
                )
            if not self.faiss_index.is_trained:
                # IVF 训练需要训练样本数 >= nlist；否则降级为 Flat 索引（无需训练）
                n_train = int(embeddings_f32.shape[0])
                nlist = int(getattr(self.faiss_index, "nlist", 0) or 0)
                if nlist and n_train < nlist:
                    logger.warning(
                        "训练样本数(%s)小于nlist(%s)，已自动降级为 IndexFlatL2 以保证可用性",
                        n_train,
                        nlist,
                    )
                    if int(getattr(self.faiss_index, "ntotal", 0) or 0) != 0:
                        raise RuntimeError("FAISS索引已包含向量，无法在非空索引上自动降级类型")
                    self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)
                else:
                    logger.info("训练FAISS索引")
                    self.faiss_index.train(embeddings_f32)
            
            # 批量插入知识点
            for i in range(0, len(knowledge_items), batch_size):
                batch_items = knowledge_items[i:i+batch_size]
                batch_embeddings = embeddings_f32[i:i+batch_size]
                
                for item, embedding in zip(batch_items, batch_embeddings):
                    try:
                        # 使用保存点，避免“INSERT 已提交但 embedding_id 未写入”的不一致数据
                        cursor.execute("SAVEPOINT kb_item")

                        # 插入知识点到PostgreSQL
                        cursor.execute("""
                            INSERT INTO knowledge 
                            (document_id, content, category, regulation_type, 
                             article_number, section_number)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            document_id,
                            item['content'],
                            item.get('category'),
                            item.get('regulation_type'),
                            item.get('article_number'),
                            item.get('section_number')
                        ))
                        
                        knowledge_id = cursor.fetchone()[0]
                        
                        # 添加到FAISS索引
                        faiss_id = int(self.faiss_index.ntotal)
                        self.faiss_index.add(np.asarray([embedding], dtype=np.float32))
                        self.knowledge_id_map[str(knowledge_id)] = faiss_id
                        
                        # 更新embedding_id
                        cursor.execute("""
                            UPDATE knowledge SET embedding_id = %s WHERE id = %s
                        """, (faiss_id, knowledge_id))
                        
                        success_count += 1
                        cursor.execute("RELEASE SAVEPOINT kb_item")
                    
                    except Exception as e:
                        logger.warning(f"插入知识点失败: {e}")
                        try:
                            cursor.execute("ROLLBACK TO SAVEPOINT kb_item")
                            cursor.execute("RELEASE SAVEPOINT kb_item")
                        except Exception:
                            # 如果保存点操作也失败，让外层事务处理
                            pass
                        fail_count += 1
                
                conn.commit()
            
            # 保存索引
            self._save_faiss_index()
            
            duration = time.time() - start_time
            logger.info(f"批量导入完成: 成功{success_count}个, 失败{fail_count}个, 耗时{duration:.2f}秒")
            
            return success_count, fail_count
        
        except PgError as e:
            if conn:
                conn.rollback()
            logger.error(f"批量导入失败: {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        检索知识点
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            threshold: 相似度阈值（0-1，越高越严格）
            
        Returns:
            检索结果列表
        """
        start_time = time.time()
        
        try:
            # 生成查询向量
            query_embedding = self.embedding_model.encode(
                [query],
                convert_to_numpy=True
            )[0]
            
            # FAISS检索
            distances, indices = self.faiss_index.search(
                np.array([query_embedding], dtype=np.float32),
                top_k
            )
            
            # 转换距离为相似度（L2距离转相似度）
            # 相似度 = 1 / (1 + 距离)
            results = []
            conn = None
            
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                for idx, distance in zip(indices[0], distances[0]):
                    if idx == -1:  # FAISS返回-1表示无效结果
                        continue
                    
                    # 反向查找knowledge_id
                    knowledge_id = None
                    for kid, fid in self.knowledge_id_map.items():
                        if fid == idx:
                            knowledge_id = int(kid)
                            break
                    
                    if knowledge_id is None:
                        continue
                    
                    # 从PostgreSQL获取完整信息
                    cursor.execute("""
                        SELECT k.id, k.content, k.category, k.regulation_type,
                               k.article_number, k.section_number, d.name
                        FROM knowledge k
                        JOIN document d ON k.document_id = d.id
                        WHERE k.id = %s
                    """, (knowledge_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        similarity = 1.0 / (1.0 + distance)
                        
                        if similarity >= threshold:
                            results.append({
                                'knowledge_id': row[0],
                                'content': row[1],
                                'category': row[2],
                                'regulation_type': row[3],
                                'article_number': row[4],
                                'section_number': row[5],
                                'document_name': row[6],
                                'similarity': float(similarity),
                                'distance': float(distance)
                            })
                
                duration = time.time() - start_time
                
                # 记录检索日志
                self._log_operation(
                    operation='search',
                    status='success',
                    message=f"查询: {query}, 结果数: {len(results)}",
                    duration_ms=duration * 1000
                )
                
                logger.info(f"检索完成: {len(results)}个结果, 耗时{duration:.3f}秒")
                
                if duration > 2.0:
                    logger.warning(f"检索响应时间超过2秒: {duration:.3f}秒")
                
                return results
            
            finally:
                if conn:
                    self._return_connection(conn)
        
        except Exception as e:
            logger.error(f"检索失败: {e}")
            self._log_operation(
                operation='search',
                status='failed',
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
            raise
    
    def _save_faiss_index(self):
        """保存FAISS索引到磁盘"""
        try:
            index_file = os.path.join(self.faiss_index_path, "financial_kb.index")
            id_map_file = os.path.join(self.faiss_index_path, "id_map.json")
            
            faiss.write_index(self.faiss_index, index_file)
            
            with open(id_map_file, 'w') as f:
                json.dump(self.knowledge_id_map, f)
            
            logger.info(f"FAISS索引已保存到 {index_file}")
        
        except Exception as e:
            logger.error(f"保存FAISS索引失败: {e}")
            raise
    
    def _log_operation(
        self,
        operation: str,
        status: str = None,
        message: str = None,
        duration_ms: float = None,
        knowledge_id: int = None
    ):
        """记录操作日志"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO log (operation, knowledge_id, status, message, duration_ms)
                VALUES (%s, %s, %s, %s, %s)
            """, (operation, knowledge_id, status, message, duration_ms))
            
            conn.commit()
        
        except PgError as e:
            logger.warning(f"记录日志失败: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_statistics(self) -> Dict:
        """获取知识库统计信息"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 文档数量
            cursor.execute("SELECT COUNT(*) FROM document")
            doc_count = cursor.fetchone()[0]
            
            # 知识点数量
            cursor.execute("SELECT COUNT(*) FROM knowledge")
            knowledge_count = cursor.fetchone()[0]
            
            # 分类统计
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM knowledge
                WHERE category IS NOT NULL
                GROUP BY category
            """)
            category_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 监管类型统计
            cursor.execute("""
                SELECT regulation_type, COUNT(*) as count
                FROM knowledge
                WHERE regulation_type IS NOT NULL
                GROUP BY regulation_type
            """)
            regulation_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'document_count': doc_count,
                'knowledge_count': knowledge_count,
                'faiss_index_size': len(self.knowledge_id_map),
                'category_distribution': category_stats,
                'regulation_distribution': regulation_stats
            }
        
        except PgError as e:
            logger.error(f"获取统计信息失败: {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def close(self):
        """关闭连接池"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("连接池已关闭")

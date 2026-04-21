"""
Financial knowledge base service backed by MySQL + Milvus.
"""

import logging
import os
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import numpy as np
import pymysql
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """Knowledge base service for document storage and vector retrieval."""

    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 3306,
        db_name: str = "finregqa",
        db_user: str = "root",
        db_password: str = "password",
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        milvus_uri: str = "http://127.0.0.1:19530",
        milvus_token: str = "",
        milvus_collection_name: str = "financial_knowledge",
        max_connections: int = 10,
        embedding_dim: int = 768,
    ):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.embedding_model_name = embedding_model
        self.embedding_dim = embedding_dim
        self.milvus_uri = milvus_uri
        self.milvus_token = milvus_token
        self.milvus_collection_name = milvus_collection_name
        self.vector_field_name = "vector"

        self.connection_pool = None
        self.milvus_client: Optional[MilvusClient] = None

        self._init_connection_pool(max_connections)

        logger.info("Loading embedding model: %s", embedding_model)
        self.embedding_model = SentenceTransformer(embedding_model)

        try:
            model_dim = int(self.embedding_model.get_sentence_embedding_dimension())
            if model_dim != self.embedding_dim:
                logger.warning(
                    "Configured embedding_dim=%s does not match model_dim=%s; using model dimension",
                    self.embedding_dim,
                    model_dim,
                )
                self.embedding_dim = model_dim
        except Exception as exc:
            logger.warning("Failed to read embedding model dimension: %s", exc)

        self._init_milvus()
        self._init_database()

    def _init_connection_pool(self, max_connections: int) -> None:
        """Initialize the MySQL connection pool."""

        def _creator():
            return pymysql.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                charset="utf8mb4",
                autocommit=False,
                connect_timeout=5,
                cursorclass=pymysql.cursors.Cursor,
            )

        try:
            self.connection_pool = QueuePool(
                creator=_creator,
                pool_size=max_connections,
                max_overflow=0,
                recycle=3600,
            )
            logger.info("MySQL connection pool initialized (max connections: %s)", max_connections)
        except Exception as exc:
            logger.error("Failed to initialize connection pool: %s", exc)
            raise

    def _get_connection(self):
        """Get a connection from the pool."""
        return self.connection_pool.connect()

    def _return_connection(self, conn) -> None:
        """Return a pooled connection."""
        if conn:
            conn.close()

    def _uses_local_milvus_file(self) -> bool:
        parsed = urlparse(self.milvus_uri)
        return parsed.scheme == "" and self.milvus_uri.lower().endswith(".db")

    def _ensure_local_milvus_dir(self) -> None:
        if self._uses_local_milvus_file():
            milvus_path = os.path.abspath(self.milvus_uri)
            os.makedirs(os.path.dirname(milvus_path), exist_ok=True)

    def _init_milvus(self) -> None:
        """Initialize the Milvus client and collection."""
        self._ensure_local_milvus_dir()

        try:
            kwargs = {"uri": self.milvus_uri}
            if self.milvus_token:
                kwargs["token"] = self.milvus_token
            self.milvus_client = MilvusClient(**kwargs)
        except Exception as exc:
            if self._uses_local_milvus_file() and os.name == "nt":
                raise RuntimeError(
                    "Milvus Lite local file mode is not available in the current Windows setup. "
                    "Run a Milvus server and set MILVUS_URI to an address like http://127.0.0.1:19530."
                ) from exc
            raise

        if not self.milvus_client.has_collection(self.milvus_collection_name):
            logger.info(
                "Creating Milvus collection %s (dim=%s)",
                self.milvus_collection_name,
                self.embedding_dim,
            )
            self.milvus_client.create_collection(
                collection_name=self.milvus_collection_name,
                dimension=self.embedding_dim,
                primary_field_name="id",
                vector_field_name=self.vector_field_name,
                metric_type="COSINE",
                auto_id=False,
            )

        try:
            self.milvus_client.load_collection(self.milvus_collection_name)
        except Exception:
            # Milvus Lite does not require an explicit load step.
            pass

    def _table_exists(self, cursor, table_name: str) -> bool:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return cursor.fetchone() is not None

    def _column_exists(self, cursor, table_name: str, column_name: str) -> bool:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
        return cursor.fetchone() is not None

    def _index_exists(self, cursor, table_name: str, index_name: str) -> bool:
        cursor.execute(f"SHOW INDEX FROM `{table_name}` WHERE Key_name = %s", (index_name,))
        return cursor.fetchone() is not None

    def _ensure_index(self, cursor, table_name: str, index_name: str, columns_sql: str) -> None:
        if not self._index_exists(cursor, table_name, index_name):
            cursor.execute(f"CREATE INDEX `{index_name}` ON `{table_name}` ({columns_sql})")

    def _init_database(self) -> None:
        """Initialize MySQL tables for the knowledge base."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS document (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    source VARCHAR(255),
                    file_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    document_id INT NOT NULL,
                    content LONGTEXT NOT NULL,
                    category VARCHAR(100),
                    region VARCHAR(100),
                    regulation_type VARCHAR(100),
                    article_number VARCHAR(50),
                    section_number VARCHAR(50),
                    embedding_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_knowledge_document
                        FOREIGN KEY (document_id) REFERENCES document(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    operation VARCHAR(50) NOT NULL,
                    knowledge_id INT NULL,
                    status VARCHAR(20),
                    message TEXT,
                    duration_ms FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_log_knowledge
                        FOREIGN KEY (knowledge_id) REFERENCES knowledge(id)
                        ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            if not self._column_exists(cursor, "knowledge", "region"):
                cursor.execute("ALTER TABLE knowledge ADD COLUMN region VARCHAR(100)")

            self._ensure_index(cursor, "knowledge", "idx_knowledge_document_id", "document_id")
            self._ensure_index(cursor, "knowledge", "idx_knowledge_category", "category")
            self._ensure_index(cursor, "knowledge", "idx_knowledge_region", "region")
            self._ensure_index(cursor, "knowledge", "idx_knowledge_article", "article_number")

            conn.commit()
            logger.info("Knowledge base tables initialized")
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Failed to initialize knowledge base tables: %s", exc)
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def add_document(self, name: str, source: str = None, file_type: str = None) -> int:
        """Add a document record."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO document (name, source, file_type) VALUES (%s, %s, %s)",
                (name, source, file_type),
            )
            doc_id = int(cursor.lastrowid)
            conn.commit()
            logger.info("Document added: %s (id=%s)", name, doc_id)
            return doc_id
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Failed to add document: %s", exc)
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def _insert_vector(self, knowledge_id: int, embedding: np.ndarray) -> None:
        self.milvus_client.insert(
            self.milvus_collection_name,
            [{"id": knowledge_id, self.vector_field_name: embedding.tolist()}],
        )

    def _delete_vector(self, knowledge_id: int) -> None:
        try:
            self.milvus_client.delete(self.milvus_collection_name, ids=[knowledge_id])
        except Exception as exc:
            logger.warning("Failed to delete Milvus vector id=%s: %s", knowledge_id, exc)

    def add_knowledge_batch(
        self, document_id: int, knowledge_items: List[Dict], batch_size: int = 100
    ) -> Tuple[int, int]:
        """Insert a batch of knowledge items."""
        start_time = time.time()
        success_count = 0
        fail_count = 0
        conn = None

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            contents = [item["content"] for item in knowledge_items]
            embeddings = self.embedding_model.encode(
                contents,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True,
            )

            embeddings_f32 = embeddings.astype(np.float32, copy=False)
            if embeddings_f32.ndim != 2 or embeddings_f32.shape[1] != self.embedding_dim:
                raise ValueError(
                    f"Embedding dimension mismatch: embeddings.shape={embeddings_f32.shape}, "
                    f"expected_dim={self.embedding_dim}"
                )

            for i in range(0, len(knowledge_items), batch_size):
                batch_items = knowledge_items[i : i + batch_size]
                batch_embeddings = embeddings_f32[i : i + batch_size]

                for item, embedding in zip(batch_items, batch_embeddings):
                    knowledge_id = None
                    vector_inserted = False
                    try:
                        cursor.execute("SAVEPOINT kb_item")
                        cursor.execute(
                            """
                            INSERT INTO knowledge (
                                document_id, content, category, region,
                                regulation_type, article_number, section_number
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                document_id,
                                item["content"],
                                item.get("category"),
                                item.get("region"),
                                item.get("regulation_type"),
                                item.get("article_number"),
                                item.get("section_number"),
                            ),
                        )

                        knowledge_id = int(cursor.lastrowid)
                        self._insert_vector(knowledge_id, embedding)
                        vector_inserted = True

                        cursor.execute(
                            "UPDATE knowledge SET embedding_id = %s WHERE id = %s",
                            (knowledge_id, knowledge_id),
                        )
                        success_count += 1
                        cursor.execute("RELEASE SAVEPOINT kb_item")
                    except Exception as exc:
                        if vector_inserted and knowledge_id is not None:
                            self._delete_vector(knowledge_id)
                        logger.warning("Failed to insert knowledge item: %s", exc)
                        try:
                            cursor.execute("ROLLBACK TO SAVEPOINT kb_item")
                            cursor.execute("RELEASE SAVEPOINT kb_item")
                        except Exception:
                            pass
                        fail_count += 1

                conn.commit()

            if success_count > 0:
                self.milvus_client.flush(self.milvus_collection_name)
                try:
                    self.milvus_client.load_collection(self.milvus_collection_name)
                except Exception:
                    pass

            duration = time.time() - start_time
            logger.info(
                "Batch import finished: success=%s fail=%s duration=%.2fs",
                success_count,
                fail_count,
                duration,
            )
            return success_count, fail_count
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Batch import failed: %s", exc)
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
        region: Optional[str] = None,
    ) -> List[Dict]:
        """Search knowledge items by vector similarity."""
        start_time = time.time()
        try:
            try:
                self.milvus_client.load_collection(self.milvus_collection_name)
            except Exception:
                pass
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0].astype(np.float32)
            search_results = self.milvus_client.search(
                self.milvus_collection_name,
                data=[query_embedding.tolist()],
                limit=top_k,
                anns_field=self.vector_field_name,
                search_params={"metric_type": "COSINE"},
            )

            results = []
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                for hit in search_results[0]:
                    knowledge_id = int(hit["id"])
                    similarity = float(hit["distance"])

                    if similarity < threshold:
                        continue

                    if region:
                        cursor.execute(
                            """
                            SELECT k.id, k.content, k.category, k.region, k.regulation_type,
                                   k.article_number, k.section_number, d.name
                            FROM knowledge k
                            JOIN document d ON k.document_id = d.id
                            WHERE k.id = %s AND k.region = %s
                            """,
                            (knowledge_id, region),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT k.id, k.content, k.category, k.region, k.regulation_type,
                                   k.article_number, k.section_number, d.name
                            FROM knowledge k
                            JOIN document d ON k.document_id = d.id
                            WHERE k.id = %s
                            """,
                            (knowledge_id,),
                        )

                    row = cursor.fetchone()
                    if row:
                        results.append(
                            {
                                "knowledge_id": row[0],
                                "content": row[1],
                                "category": row[2],
                                "region": row[3],
                                "regulation_type": row[4],
                                "article_number": row[5],
                                "section_number": row[6],
                                "document_name": row[7],
                                "similarity": similarity,
                                "distance": similarity,
                            }
                        )

                duration = time.time() - start_time
                self._log_operation(
                    "search",
                    "success",
                    f"query={query}, results={len(results)}",
                    duration * 1000,
                )
                logger.info("Search finished: %s results in %.3fs", len(results), duration)
                if duration > 2.0:
                    logger.warning("Slow search response: %.3fs", duration)
                return results
            finally:
                if conn:
                    self._return_connection(conn)
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            raise

    def _log_operation(
        self,
        operation: str,
        status: str = None,
        message: str = None,
        duration_ms: float = None,
        knowledge_id: int = None,
    ) -> None:
        """Record an operation log row."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO log (operation, knowledge_id, status, message, duration_ms)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (operation, knowledge_id, status, message, duration_ms),
            )
            conn.commit()
        except Exception as exc:
            logger.warning("Failed to write operation log: %s", exc)
        finally:
            if conn:
                self._return_connection(conn)

    def get_statistics(self) -> Dict:
        """Return summary statistics for the knowledge base."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM document")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge")
            knowledge_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT category, COUNT(*) AS count
                FROM knowledge
                WHERE category IS NOT NULL
                GROUP BY category
                """
            )
            category_stats = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT regulation_type, COUNT(*) AS count
                FROM knowledge
                WHERE regulation_type IS NOT NULL
                GROUP BY regulation_type
                """
            )
            regulation_stats = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT region, COUNT(*) AS count
                FROM knowledge
                WHERE region IS NOT NULL
                GROUP BY region
                """
            )
            region_stats = {row[0]: row[1] for row in cursor.fetchall()}

            vector_index_size = 0
            if self.milvus_client.has_collection(self.milvus_collection_name):
                stats = self.milvus_client.get_collection_stats(self.milvus_collection_name)
                vector_index_size = int(stats.get("row_count", 0))

            return {
                "document_count": doc_count,
                "knowledge_count": knowledge_count,
                "vector_index_size": vector_index_size,
                "category_distribution": category_stats,
                "regulation_distribution": regulation_stats,
                "region_distribution": region_stats,
            }
        except Exception as exc:
            logger.error("Failed to get statistics: %s", exc)
            raise
        finally:
            if conn:
                self._return_connection(conn)

    def close(self) -> None:
        """Dispose the MySQL connection pool and Milvus client."""
        if self.connection_pool:
            self.connection_pool.dispose()
            logger.info("Knowledge base connection pool closed")
        if self.milvus_client:
            self.milvus_client.close()

"""
本地 Zep 替代 —— SQLite 存储层

所有数据（图谱、episode、节点、边、向量）存于单个 SQLite 文件，无需服务器/Docker。
节点/边的向量以 float32 bytes 存于 BLOB 列。
线程安全：每次操作用独立连接（check_same_thread=False + 短事务）。
"""

import json
import os
import sqlite3
import threading
import uuid as _uuid
from typing import Any, Dict, List, Optional

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS graphs (
    graph_id     TEXT PRIMARY KEY,
    name         TEXT,
    description  TEXT,
    ontology     TEXT,           -- JSON: {entity_types:[...], edge_types:[...]}
    created_at   TEXT
);
CREATE TABLE IF NOT EXISTS episodes (
    uuid        TEXT PRIMARY KEY,
    graph_id    TEXT,
    data        TEXT,
    type        TEXT,
    processed   INTEGER DEFAULT 1,
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS nodes (
    uuid        TEXT PRIMARY KEY,
    graph_id    TEXT,
    name        TEXT,
    name_key    TEXT,            -- lower(name)，用于去重
    labels      TEXT,            -- JSON list
    summary     TEXT,
    attributes  TEXT,            -- JSON dict
    embedding   BLOB,            -- float32 bytes
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS edges (
    uuid              TEXT PRIMARY KEY,
    graph_id          TEXT,
    name              TEXT,
    fact              TEXT,
    source_node_uuid  TEXT,
    target_node_uuid  TEXT,
    attributes        TEXT,      -- JSON dict
    embedding         BLOB,
    created_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_nodes_graph ON nodes(graph_id);
CREATE INDEX IF NOT EXISTS idx_nodes_key   ON nodes(graph_id, name_key);
CREATE INDEX IF NOT EXISTS idx_edges_graph ON edges(graph_id);
CREATE INDEX IF NOT EXISTS idx_edges_src   ON edges(source_node_uuid);
CREATE INDEX IF NOT EXISTS idx_edges_tgt   ON edges(target_node_uuid);
CREATE INDEX IF NOT EXISTS idx_episodes_graph ON episodes(graph_id);
"""


def _now() -> str:
    # 避免依赖不可用的时间源；用简单计数式时间戳字符串即可（仅用于展示/排序参考）
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _new_uuid() -> str:
    return _uuid.uuid4().hex


def _to_blob(vec: Optional[np.ndarray]) -> Optional[bytes]:
    if vec is None:
        return None
    return np.asarray(vec, dtype=np.float32).tobytes()


def _from_blob(blob: Optional[bytes]) -> Optional[np.ndarray]:
    if not blob:
        return None
    return np.frombuffer(blob, dtype=np.float32)


class GraphStore:
    """SQLite 后端。所有方法自带连接管理，可跨线程调用。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # ---------- graph ----------
    def create_graph(self, graph_id: str, name: str = "", description: str = ""):
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO graphs(graph_id, name, description, ontology, created_at) "
                "VALUES(?,?,?,?,?)",
                (graph_id, name, description, json.dumps({"entity_types": [], "edge_types": []}), _now()),
            )

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE graphs SET ontology=? WHERE graph_id=?",
                (json.dumps(ontology, ensure_ascii=False), graph_id),
            )

    def get_ontology(self, graph_id: str) -> Dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute("SELECT ontology FROM graphs WHERE graph_id=?", (graph_id,)).fetchone()
        if row and row["ontology"]:
            try:
                return json.loads(row["ontology"])
            except Exception:
                pass
        return {"entity_types": [], "edge_types": []}

    def delete_graph(self, graph_id: str):
        with self._lock, self._conn() as conn:
            for t in ("nodes", "edges", "episodes", "graphs"):
                col = "graph_id"
                conn.execute(f"DELETE FROM {t} WHERE {col}=?", (graph_id,))

    # ---------- episode ----------
    def add_episode(self, graph_id: str, data: str, type_: str = "text") -> str:
        ep_uuid = _new_uuid()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO episodes(uuid, graph_id, data, type, processed, created_at) VALUES(?,?,?,?,1,?)",
                (ep_uuid, graph_id, data, type_, _now()),
            )
        return ep_uuid

    def episode_processed(self, ep_uuid: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT processed FROM episodes WHERE uuid=?", (ep_uuid,)).fetchone()
        return bool(row["processed"]) if row else True

    # ---------- node ----------
    def find_node_by_name(self, graph_id: str, name: str) -> Optional[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM nodes WHERE graph_id=? AND name_key=? LIMIT 1",
                (graph_id, (name or "").strip().lower()),
            ).fetchone()

    def upsert_node(
        self,
        graph_id: str,
        name: str,
        labels: List[str],
        summary: str,
        attributes: Dict[str, Any],
        embedding: Optional[np.ndarray] = None,
    ) -> str:
        """按 (graph_id, lower(name)) 去重。已存在则合并 labels/summary/attributes。"""
        name_key = (name or "").strip().lower()
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE graph_id=? AND name_key=? LIMIT 1",
                (graph_id, name_key),
            ).fetchone()
            if row:
                node_uuid = row["uuid"]
                old_labels = json.loads(row["labels"] or "[]")
                merged_labels = list(dict.fromkeys(old_labels + (labels or [])))
                old_attrs = json.loads(row["attributes"] or "{}")
                old_attrs.update({k: v for k, v in (attributes or {}).items() if v})
                new_summary = summary or row["summary"] or ""
                conn.execute(
                    "UPDATE nodes SET labels=?, summary=?, attributes=?, embedding=COALESCE(?, embedding) WHERE uuid=?",
                    (json.dumps(merged_labels, ensure_ascii=False), new_summary,
                     json.dumps(old_attrs, ensure_ascii=False), _to_blob(embedding), node_uuid),
                )
                return node_uuid
            node_uuid = _new_uuid()
            conn.execute(
                "INSERT INTO nodes(uuid, graph_id, name, name_key, labels, summary, attributes, embedding, created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (node_uuid, graph_id, name, name_key,
                 json.dumps(labels or [], ensure_ascii=False), summary or "",
                 json.dumps(attributes or {}, ensure_ascii=False), _to_blob(embedding), _now()),
            )
            return node_uuid

    def get_nodes(self, graph_id: str, limit: int = 100, after_uuid: Optional[str] = None) -> List[sqlite3.Row]:
        """按 uuid 排序分页（uuid_cursor 语义）。"""
        with self._conn() as conn:
            if after_uuid:
                return conn.execute(
                    "SELECT * FROM nodes WHERE graph_id=? AND uuid>? ORDER BY uuid ASC LIMIT ?",
                    (graph_id, after_uuid, limit),
                ).fetchall()
            return conn.execute(
                "SELECT * FROM nodes WHERE graph_id=? ORDER BY uuid ASC LIMIT ?",
                (graph_id, limit),
            ).fetchall()

    def get_node(self, node_uuid: str) -> Optional[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM nodes WHERE uuid=?", (node_uuid,)).fetchone()

    def all_nodes(self, graph_id: str) -> List[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM nodes WHERE graph_id=?", (graph_id,)).fetchall()

    # ---------- edge ----------
    def upsert_edge(
        self,
        graph_id: str,
        name: str,
        fact: str,
        source_node_uuid: str,
        target_node_uuid: str,
        attributes: Dict[str, Any],
        embedding: Optional[np.ndarray] = None,
    ) -> str:
        edge_uuid = _new_uuid()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO edges(uuid, graph_id, name, fact, source_node_uuid, target_node_uuid, attributes, embedding, created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (edge_uuid, graph_id, name or "", fact or "", source_node_uuid or "", target_node_uuid or "",
                 json.dumps(attributes or {}, ensure_ascii=False), _to_blob(embedding), _now()),
            )
        return edge_uuid

    def get_edges(self, graph_id: str, limit: int = 100, after_uuid: Optional[str] = None) -> List[sqlite3.Row]:
        with self._conn() as conn:
            if after_uuid:
                return conn.execute(
                    "SELECT * FROM edges WHERE graph_id=? AND uuid>? ORDER BY uuid ASC LIMIT ?",
                    (graph_id, after_uuid, limit),
                ).fetchall()
            return conn.execute(
                "SELECT * FROM edges WHERE graph_id=? ORDER BY uuid ASC LIMIT ?",
                (graph_id, limit),
            ).fetchall()

    def get_edges_for_node(self, node_uuid: str) -> List[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM edges WHERE source_node_uuid=? OR target_node_uuid=?",
                (node_uuid, node_uuid),
            ).fetchall()

    def all_edges(self, graph_id: str) -> List[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM edges WHERE graph_id=?", (graph_id,)).fetchall()

    # ---------- helpers ----------
    @staticmethod
    def row_embedding(row: sqlite3.Row) -> Optional[np.ndarray]:
        return _from_blob(row["embedding"]) if row is not None and "embedding" in row.keys() else None

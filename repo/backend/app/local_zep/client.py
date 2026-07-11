"""
本地 Zep 替代 —— LocalZep 客户端

复刻 zep_cloud.client.Zep 被 MiroFish 使用的 API 表面：
  client.graph.create / set_ontology / add_batch / add / search / delete
  client.graph.episode.get(uuid_)                -> .processed
  client.graph.node.get_by_graph_id / get / get_entity_edges
  client.graph.edge.get_by_graph_id

抽取用服务中的 Qwen3.6-27B（HTTP），嵌入/重排用本地 Qwen 0.6B，存储用 SQLite。
"""

import json
import os
import uuid as _uuid
from typing import Any, Dict, List, Optional

import numpy as np

from ..utils.logger import get_logger
from . import embedder, reranker
from .extractor import Extractor
from .models import SearchResult, make_edge, make_episode, make_node
from .ontology import introspect_edge_types, introspect_entity_types
from .store import GraphStore

logger = get_logger("mirofish.local_zep")


def _default_db_path() -> str:
    # 默认放在 backend/app/uploads/local_graph.db
    env = os.environ.get("LOCAL_GRAPH_DB")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "uploads", "local_graph.db")


# 进程内共享单个 store（同一 SQLite 文件），避免每个客户端重复建连
_shared_store: Optional[GraphStore] = None


def _get_store() -> GraphStore:
    global _shared_store
    if _shared_store is None:
        _shared_store = GraphStore(_default_db_path())
    return _shared_store


def _node_obj(row) -> Any:
    return make_node(
        uuid=row["uuid"],
        name=row["name"],
        labels=json.loads(row["labels"] or "[]"),
        summary=row["summary"] or "",
        attributes=json.loads(row["attributes"] or "{}"),
    )


def _edge_obj(row) -> Any:
    return make_edge(
        uuid=row["uuid"],
        name=row["name"],
        fact=row["fact"],
        source_node_uuid=row["source_node_uuid"],
        target_node_uuid=row["target_node_uuid"],
        attributes=json.loads(row["attributes"] or "{}"),
    )


class _EpisodeNS:
    def __init__(self, store: GraphStore):
        self._store = store

    def get(self, uuid_: str = None, **kw):
        uid = uuid_ or kw.get("uuid")
        return make_episode(uid, processed=self._store.episode_processed(uid))


class _NodeNS:
    def __init__(self, store: GraphStore):
        self._store = store

    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: str = None, **kw):
        rows = self._store.get_nodes(graph_id, limit=limit, after_uuid=uuid_cursor)
        return [_node_obj(r) for r in rows]

    def get(self, uuid_: str = None, **kw):
        uid = uuid_ or kw.get("uuid")
        row = self._store.get_node(uid)
        return _node_obj(row) if row else None

    def get_entity_edges(self, node_uuid: str = None, **kw):
        uid = node_uuid or kw.get("uuid_") or kw.get("uuid")
        return [_edge_obj(r) for r in self._store.get_edges_for_node(uid)]


class _EdgeNS:
    def __init__(self, store: GraphStore):
        self._store = store

    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: str = None, **kw):
        rows = self._store.get_edges(graph_id, limit=limit, after_uuid=uuid_cursor)
        return [_edge_obj(r) for r in rows]


class _GraphNS:
    def __init__(self, store: GraphStore, llm=None, embed_cfg=None, rerank_cfg=None):
        self._store = store
        self._extractor = Extractor(llm=llm)   # llm=None이면 Config(로컬 Qwen) 기본
        # 임베더/리랭커 provider 설정({provider, api_key, model}). None이면 로컬 Qwen.
        self._embed_cfg = embed_cfg or {}
        self._rerank_cfg = rerank_cfg or {}
        self.node = _NodeNS(store)
        self.edge = _EdgeNS(store)
        self.episode = _EpisodeNS(store)

    # ---------- 图谱生命周期 ----------
    def create(self, graph_id: str = None, name: str = "", description: str = "", **kw):
        gid = graph_id or kw.get("graph_id") or f"mirofish_{_uuid.uuid4().hex[:16]}"
        self._store.create_graph(gid, name=name or "", description=description or "")
        return make_node(uuid=gid, name=name or "")  # 返回带属性的对象，调用方一般不读返回值

    def set_ontology(self, graph_ids: List[str] = None, entities=None, edges=None, **kw):
        ontology = {
            "entity_types": introspect_entity_types(entities),
            "edge_types": introspect_edge_types(edges),
        }
        for gid in (graph_ids or []):
            self._store.set_ontology(gid, ontology)
        logger.info(f"set_ontology: {len(ontology['entity_types'])} 实体类型, "
                    f"{len(ontology['edge_types'])} 关系类型 -> {graph_ids}")

    def delete(self, graph_id: str = None, **kw):
        self._store.delete_graph(graph_id or kw.get("graph_id"))

    # ---------- 写入（触发同步抽取）----------
    def add_batch(self, graph_id: str = None, episodes: List[Any] = None, **kw):
        gid = graph_id or kw.get("graph_id")
        results = []
        for ep in (episodes or []):
            data = getattr(ep, "data", None) or (ep.get("data") if isinstance(ep, dict) else str(ep))
            ep_uuid = self._ingest(gid, data)
            results.append(make_episode(ep_uuid))
        return results

    def add(self, graph_id: str = None, type: str = "text", data: str = None, **kw):
        gid = graph_id or kw.get("graph_id")
        ep_uuid = self._ingest(gid, data or "")
        return make_episode(ep_uuid)

    def _ingest(self, graph_id: str, text: str) -> str:
        """存 episode -> LLM 抽取 -> upsert 节点/边（含嵌入）。同步完成。"""
        ep_uuid = self._store.add_episode(graph_id, text or "")
        try:
            ontology = self._store.get_ontology(graph_id)
            extracted = self._extractor.extract(text, ontology)
        except Exception as e:
            logger.warning(f"抽取阶段异常，episode 仍保留: {str(e)[:120]}")
            return ep_uuid

        entities = extracted.get("entities", [])
        relations = extracted.get("relations", [])

        # 嵌入实体（用 name + summary）与关系（用 fact）
        name_to_uuid: Dict[str, str] = {}
        if entities:
            ent_texts = [f"{e['name']}. {e.get('summary','')}".strip() for e in entities]
            ent_vecs = _safe_embed(ent_texts, self._embed_cfg)
            for e, vec in zip(entities, ent_vecs):
                node_uuid = self._store.upsert_node(
                    graph_id=graph_id,
                    name=e["name"],
                    labels=[e.get("type", "Entity"), "Entity"],
                    summary=e.get("summary", ""),
                    attributes=e.get("attributes", {}),
                    embedding=vec,
                )
                name_to_uuid[e["name"].strip().lower()] = node_uuid

        if relations:
            rel_texts = [r.get("fact") or f"{r['source']} {r.get('type','')} {r['target']}" for r in relations]
            rel_vecs = _safe_embed(rel_texts, self._embed_cfg)
            for r, vec in zip(relations, rel_vecs):
                src = name_to_uuid.get(r["source"].strip().lower())
                tgt = name_to_uuid.get(r["target"].strip().lower())
                # 关系端点可能是本片段未新建的已有节点
                if not src:
                    row = self._store.find_node_by_name(graph_id, r["source"])
                    src = row["uuid"] if row else self._store.upsert_node(
                        graph_id, r["source"], ["Entity"], "", {})
                if not tgt:
                    row = self._store.find_node_by_name(graph_id, r["target"])
                    tgt = row["uuid"] if row else self._store.upsert_node(
                        graph_id, r["target"], ["Entity"], "", {})
                self._store.upsert_edge(
                    graph_id=graph_id,
                    name=r.get("type", "related_to"),
                    fact=r.get("fact", ""),
                    source_node_uuid=src,
                    target_node_uuid=tgt,
                    attributes=r.get("attributes", {}),
                    embedding=vec,
                )
        return ep_uuid

    # ---------- 检索 ----------
    def search(self, graph_id: str = None, query: str = "", limit: int = 10,
               scope: str = "edges", reranker: str = None, **kw):
        gid = graph_id or kw.get("graph_id")
        if scope == "nodes":
            return SearchResult(edges=[], nodes=self._search_nodes(gid, query, limit, reranker))
        return SearchResult(edges=self._search_edges(gid, query, limit, reranker), nodes=[])

    def _search_edges(self, graph_id, query, limit, reranker_flag):
        rows = self._store.all_edges(graph_id)
        if not rows:
            return []
        texts = [r["fact"] or r["name"] or "" for r in rows]
        ranked_idx = _hybrid_rank(query, rows, texts, limit, reranker_flag,
                                  self._embed_cfg, self._rerank_cfg)
        return [_edge_obj(rows[i]) for i in ranked_idx]

    def _search_nodes(self, graph_id, query, limit, reranker_flag):
        rows = self._store.all_nodes(graph_id)
        if not rows:
            return []
        texts = [f"{r['name']}. {r['summary'] or ''}".strip() for r in rows]
        ranked_idx = _hybrid_rank(query, rows, texts, limit, reranker_flag,
                                  self._embed_cfg, self._rerank_cfg)
        return [_node_obj(rows[i]) for i in ranked_idx]


def _safe_embed(texts: List[str], embed_cfg: dict = None) -> List[Optional[np.ndarray]]:
    cfg = embed_cfg or {}
    try:
        vecs = embedder.embed(texts, is_query=False,
                              provider=cfg.get("provider"), api_key=cfg.get("api_key"),
                              model=cfg.get("model"))
        return [vecs[i] for i in range(len(texts))]
    except Exception as e:
        logger.warning(f"嵌入失败，节点/边将无向量（仅关键词可检索）: {str(e)[:120]}")
        return [None] * len(texts)


def _hybrid_rank(query: str, rows, texts: List[str], limit: int, reranker_flag,
                 embed_cfg: dict = None, rerank_cfg: dict = None) -> List[int]:
    """嵌入初排 -> （可选）重排。嵌入不可用时退化为关键词匹配。"""
    ecfg = embed_cfg or {}
    rcfg = rerank_cfg or {}
    # 收集已有向量
    stored = [GraphStore.row_embedding(r) for r in rows]
    have_vecs = all(v is not None for v in stored)

    prelim: List[int]
    if have_vecs:
        try:
            qv = embedder.embed_one(query, is_query=True,
                                    provider=ecfg.get("provider"), api_key=ecfg.get("api_key"),
                                    model=ecfg.get("model"))
            cand = np.vstack(stored).astype(np.float32)
            prelim = embedder.cosine_topk(qv, cand, max(limit * 4, limit))
        except Exception as e:
            logger.warning(f"向量检索失败，退化关键词: {str(e)[:100]}")
            prelim = _keyword_rank(query, texts, max(limit * 4, limit))
    else:
        prelim = _keyword_rank(query, texts, max(limit * 4, limit))

    # 重排（reranker 请求且模型启用时）
    if reranker_flag and reranker.enabled(rcfg.get("provider"), rcfg.get("api_key")) and prelim:
        try:
            docs = [texts[i] for i in prelim]
            order = reranker.rerank(query, docs, top_k=limit,
                                    provider=rcfg.get("provider"), api_key=rcfg.get("api_key"),
                                    model=rcfg.get("model"))
            return [prelim[i] for i, _ in order]
        except Exception as e:
            logger.warning(f"重排失败，用初排结果: {str(e)[:100]}")
    return prelim[:limit]


def _keyword_rank(query: str, texts: List[str], k: int) -> List[int]:
    q_terms = [t for t in (query or "").lower().split() if t]
    scored = []
    for i, txt in enumerate(texts):
        low = (txt or "").lower()
        score = sum(low.count(t) for t in q_terms) if q_terms else 0
        # 无查询词时也给个基线，保证有返回
        scored.append((i, score if q_terms else 1))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [i for i, _ in scored[:k]]


class Zep:
    """drop-in 替代 zep_cloud.client.Zep。忽略 api_key。

    providers(dict, 선택): {llm:{...}, embed:{provider,api_key,model}, rerank:{...}}
    → LLM 추출/임베딩/리랭킹을 local(Qwen) 또는 cloud(OpenAI+Voyage)로 전환.
    """

    def __init__(self, api_key: str = None, providers: dict = None,
                 llm_base_url: str = None, llm_model: str = None, llm_api_key: str = None,
                 embed_cfg: dict = None, rerank_cfg: dict = None, **kwargs):
        self._store = _get_store()

        # providers 묶음이 오면 개별 인자로 분해(둘 중 아무 방식이나 허용)
        if providers:
            _llm = providers.get("llm") or {}
            llm_base_url = llm_base_url or _llm.get("base_url")
            llm_model = llm_model or _llm.get("model")
            llm_api_key = llm_api_key or _llm.get("api_key")
            embed_cfg = embed_cfg or providers.get("embed")
            rerank_cfg = rerank_cfg or providers.get("rerank")

        # 그래프 추출(LLM) 오버라이드. 없으면 Config(로컬 Qwen) 기본.
        llm = None
        if llm_base_url or llm_model or llm_api_key:
            from ..utils.llm_client import LLMClient
            llm = LLMClient(api_key=llm_api_key, base_url=llm_base_url, model=llm_model)

        self.graph = _GraphNS(self._store, llm=llm,
                              embed_cfg=embed_cfg, rerank_cfg=rerank_cfg)

"""
Voyage AI REST 클라이언트 (임베딩 + 리랭크).

cloud 모드에서 로컬 Qwen 0.6B 임베더/리랭커 대신 사용.
voyageai SDK 없이 requests 로 직접 호출한다.
- 임베딩: POST https://api.voyageai.com/v1/embeddings  (input_type=query|document)
- 리랭크: POST https://api.voyageai.com/v1/rerank
"""
import os
import time
from typing import List, Tuple

import numpy as np
import requests

_BASE = os.environ.get("VOYAGE_BASE_URL", "https://api.voyageai.com/v1")
_TIMEOUT = float(os.environ.get("VOYAGE_TIMEOUT", "60"))
_MAX_RETRIES = int(os.environ.get("VOYAGE_MAX_RETRIES", "6"))


def _post(path: str, api_key: str, payload: dict) -> dict:
    """레이트리밋(429)·5xx 재시도(지수 백오프 + Retry-After 존중)."""
    url = f"{_BASE}/{path}"
    delay = 2.0
    last = None
    for attempt in range(_MAX_RETRIES):
        r = requests.post(url, headers=_headers(api_key), json=payload, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        last = r
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("Retry-After") or delay)
            time.sleep(min(wait, 60.0))
            delay = min(delay * 2, 60.0)
            continue
        r.raise_for_status()
    last.raise_for_status()  # 재시도 소진
# voyage-4-lite 차원 1024로 명시(로컬 Qwen과 동일). voyage-4-lite는 256/512/1024/2048 지원.
_EMBED_DIM = int(os.environ.get("VOYAGE_EMBED_DIM", "1024"))


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def embed(texts: List[str], api_key: str, model: str,
          is_query: bool = False, batch_size: int = 96) -> np.ndarray:
    """L2 정규화된 (len(texts), dim) 임베딩 반환."""
    if not texts:
        return np.zeros((0, _EMBED_DIM), dtype=np.float32)
    input_type = "query" if is_query else "document"
    out: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = {
            "input": batch,
            "model": model,
            "input_type": input_type,
            "output_dimension": _EMBED_DIM,
        }
        data = _post("embeddings", api_key, payload).get("data", [])
        # index 순서 보장
        data.sort(key=lambda d: d.get("index", 0))
        out.extend(d["embedding"] for d in data)
    arr = np.asarray(out, dtype=np.float32)
    # L2 정규화 (코사인 유사도용)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def rerank(query: str, docs: List[str], api_key: str, model: str,
           top_k: int = None) -> List[Tuple[int, float]]:
    """[(원본 인덱스, 관련도 점수)] 내림차순. top_k 절단."""
    if not docs:
        return []
    payload = {"query": query, "documents": docs, "model": model, "return_documents": False}
    if top_k:
        payload["top_k"] = top_k
    results = _post("rerank", api_key, payload).get("data", [])
    ordered = sorted(results, key=lambda d: d.get("relevance_score", 0.0), reverse=True)
    return [(int(d["index"]), float(d.get("relevance_score", 0.0))) for d in ordered]

"""
designdb 시맨틱 검색 (2단계: Voyage 임베딩 top-K → Voyage rerank top-N).

참고: taeyoung-ko/hci-paper-semantic-search 의 2단계 검색 아키텍처를
     Voyage(임베딩 input_type + rerank-2.5)로 이식.

- 인덱스: designdb 전 기사(text.txt) 전문을 Voyage로 임베딩해 저장(1024차원, 정규화).
- 검색: 제품 설명(쿼리) 임베딩 → 코사인 top-K → Voyage rerank → top-N.
- 카테고리(디렉토리 ID)별 탭 지원.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ..config import Config  # noqa: F401  (.env 로드)
from ..local_zep import voyage
from ..utils.logger import get_logger

logger = get_logger("mirofish.designdb")

# 카테고리(디렉토리 ID → 표시명)
CATEGORY_MAP: Dict[str, str] = {
    "792": "국내 디자인 뉴스",
    "1278": "디자인인사이트",
    "1280": "해외 디자인 뉴스",
    "1283": "해외 디자인리포트",
    "1432": "국내 디자인리포트",
    "1434": "기술 트렌드",
}

DESIGNDB_ROOT = os.environ.get("DESIGNDB_ROOT", "/home/taeyoung/nfs-mount/designdb/db")
INDEX_DIR = Path(os.path.join(os.path.dirname(__file__), "..", "data", "designdb_index"))
EMB_PATH = INDEX_DIR / "embeddings.npy"
META_PATH = INDEX_DIR / "meta.jsonl"

# 임베딩 입력 상한(전문이지만 토큰 폭주 방지). 대부분 기사는 이 안에 들어옴.
EMBED_MAX_CHARS = int(os.environ.get("DESIGNDB_EMBED_MAX_CHARS", "16000"))
SNIPPET_CHARS = 300


# ────────────────────────────── 파싱 ──────────────────────────────
def parse_article(path: str) -> Dict[str, str]:
    """text.txt → {title, field, date, body}. 헤더(제목/분야/등록일) + 본문 분리."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    title = field = date = ""
    body_lines: List[str] = []
    in_body = False
    for line in text.splitlines():
        if not in_body:
            s = line.strip()
            if s.startswith("제목:"):
                title = s[len("제목:"):].strip()
            elif s.startswith("분야:"):
                field = s[len("분야:"):].strip()
            elif s.startswith("등록일:"):
                date = s[len("등록일:"):].strip()
            elif s == "본문:":
                in_body = True
        else:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    if not body:
        body = text.strip()  # 본문 마커 없으면 전체
    return {"title": title, "field": field, "date": date, "body": body}


def _embed_text(art: Dict[str, str]) -> str:
    """인덱싱용 문서 텍스트(제목+본문 전문, 상한 적용)."""
    t = (art.get("title") or "").strip()
    b = (art.get("body") or "").strip()
    txt = f"{t}\n{b}" if t else b
    return txt[:EMBED_MAX_CHARS]


def iter_articles(root: Optional[str] = None):
    """(category, post_id, text.txt경로) 결정적 순서로 순회. 알려진 카테고리만."""
    base = Path(root or DESIGNDB_ROOT)
    for cat in sorted(CATEGORY_MAP.keys(), key=lambda x: int(x)):
        cat_dir = base / cat
        if not cat_dir.is_dir():
            continue
        for post_dir in sorted([p for p in cat_dir.iterdir() if p.is_dir()],
                               key=lambda p: (len(p.name), p.name)):
            tp = post_dir / "text.txt"
            if tp.exists():
                yield cat, post_dir.name, str(tp)


# ────────────────────────────── 인덱스 빌드(재개 가능) ──────────────────────────────
def build_index(limit: Optional[int] = None, embed_batch: int = 8,
                checkpoint_every: int = 25) -> Dict:
    """전 기사 파싱 → Voyage 임베딩 → embeddings.npy + meta.jsonl 저장.

    재개 가능: embeddings.npy 가 있으면 그 개수만큼 건너뛰고 이어서 임베딩.
    """
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("VOYAGE_API_KEY")
    model = os.environ.get("VOYAGE_EMBED_MODEL", "voyage-4-lite")
    if not key:
        raise RuntimeError("VOYAGE_API_KEY 미설정")

    # Phase A: 파싱(메타 + 텍스트). 순서 결정적.
    metas: List[Dict] = []
    texts: List[str] = []
    for cat, post_id, tp in iter_articles():
        art = parse_article(tp)
        if not (art["title"] or art["body"]):
            continue
        metas.append({
            "id": len(metas),
            "category": cat,
            "category_name": CATEGORY_MAP[cat],
            "post_id": post_id,
            "title": art["title"],
            "field": art["field"],
            "date": art["date"],
            "path": tp,
            "char_len": len(art["body"]),
            "snippet": art["body"][:SNIPPET_CHARS].replace("\n", " ").strip(),
        })
        texts.append(_embed_text(art))
        if limit and len(metas) >= limit:
            break

    total = len(metas)
    logger.info(f"[designdb] 파싱 완료: {total}건")

    # meta 저장(항상 최신 순서로)
    with META_PATH.open("w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    # 재개: 이미 임베딩된 개수
    done = 0
    embs: List[np.ndarray] = []
    if EMB_PATH.exists():
        try:
            prev = np.load(EMB_PATH)
            if prev.shape[0] <= total:
                done = prev.shape[0]
                embs = [prev]
                logger.info(f"[designdb] 재개: {done}/{total} 이미 완료")
        except Exception:
            done = 0

    # Phase B: 임베딩(배치)
    i = done
    since_ckpt = 0
    while i < total:
        batch = texts[i:i + embed_batch]
        vecs = voyage.embed(batch, api_key=key, model=model, is_query=False,
                            batch_size=embed_batch)
        embs.append(vecs.astype(np.float32))
        i += len(batch)
        since_ckpt += 1
        if since_ckpt >= checkpoint_every:
            np.save(EMB_PATH, np.vstack(embs))
            since_ckpt = 0
            logger.info(f"[designdb] 임베딩 {i}/{total} (체크포인트 저장)")

    if embs:
        np.save(EMB_PATH, np.vstack(embs))
    logger.info(f"[designdb] 인덱스 완료: {total}건 → {INDEX_DIR}")
    return {"count": total, "index_dir": str(INDEX_DIR)}


# ────────────────────────────── 검색(런타임) ──────────────────────────────
_emb: Optional[np.ndarray] = None
_meta: Optional[List[Dict]] = None


def _load():
    global _emb, _meta
    if _emb is None or _meta is None:
        if not (EMB_PATH.exists() and META_PATH.exists()):
            raise RuntimeError("designdb 인덱스가 없습니다. build_designdb_index.py 를 먼저 실행하세요.")
        _emb = np.load(EMB_PATH)
        with META_PATH.open(encoding="utf-8") as f:
            _meta = [json.loads(l) for l in f]
        logger.info(f"[designdb] 인덱스 로드: {_emb.shape[0]}건, dim={_emb.shape[1]}")
    return _emb, _meta


def reload_index():
    global _emb, _meta
    _emb = None
    _meta = None


def status() -> Dict:
    available = EMB_PATH.exists() and META_PATH.exists()
    count = 0
    if available:
        try:
            count = int(np.load(EMB_PATH, mmap_mode="r").shape[0])
        except Exception:
            count = 0
    cats = [{"id": k, "name": v} for k, v in
            sorted(CATEGORY_MAP.items(), key=lambda x: int(x[0]))]
    return {"available": available, "count": count, "categories": cats}


def search(query: str, category: Optional[str] = None,
           page: int = 1, page_size: int = 20, rerank_pool: int = 100) -> Dict:
    """제품 설명(query)으로 designdb 검색. category 지정 시 그 카테고리만.

    범위 내 **전체**를 코사인으로 랭킹하고(상위 rerank_pool은 Voyage rerank로 재정렬해 품질↑),
    페이지 단위로 잘라 반환 → 프론트에서 페이지 넘겨 전량 열람 가능.

    반환: {results: [...], total, page, page_size}
    """
    query = (query or "").strip()
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    if not query:
        return {"results": [], "total": 0, "page": page, "page_size": page_size}
    emb, meta = _load()
    key = os.environ.get("VOYAGE_API_KEY")
    em = os.environ.get("VOYAGE_EMBED_MODEL", "voyage-4-lite")
    rm = os.environ.get("VOYAGE_RERANK_MODEL", "rerank-2.5-lite")

    qv = voyage.embed([query], api_key=key, model=em, is_query=True)[0].astype(np.float32)
    sims = emb @ qv  # 둘 다 정규화 → 코사인

    # 범위(전체 or 카테고리) 전체를 코사인 내림차순 정렬
    if category:
        scope = [i for i in range(len(meta)) if meta[i]["category"] == category]
    else:
        scope = list(range(len(meta)))
    scope.sort(key=lambda i: -sims[i])
    total = len(scope)
    if total == 0:
        return {"results": [], "total": 0, "page": page, "page_size": page_size}

    # 상위 pool만 rerank로 재정렬(품질), 나머지는 코사인 순 유지
    score_map: Dict[int, float] = {i: float(sims[i]) for i in scope}
    pool = scope[:rerank_pool]
    order = scope
    try:
        docs = [f"{meta[i]['title']}\n{meta[i]['snippet']}" for i in pool]
        ranked = voyage.rerank(query, docs, api_key=key, model=rm, top_k=len(pool))
        reranked = [pool[local_idx] for local_idx, sc in ranked]
        for local_idx, sc in ranked:
            score_map[pool[local_idx]] = float(sc)
        order = reranked + scope[rerank_pool:]
    except Exception as e:
        logger.warning(f"[designdb] rerank 실패, 코사인 순 사용: {str(e)[:120]}")

    start = (page - 1) * page_size
    page_idx = order[start:start + page_size]
    results = []
    for i in page_idx:
        m = dict(meta[i])
        m["score"] = round(score_map.get(i, float(sims[i])), 4)
        m.pop("path", None)
        results.append(m)
    return {"results": results, "total": total, "page": page, "page_size": page_size}


def get_article(aid: int) -> Dict:
    """기사 1건의 전문 + 메타(클릭 시 상세 모달용)."""
    _, meta = _load()
    m = meta[int(aid)]
    art = parse_article(m["path"])
    return {
        "id": m["id"],
        "title": m["title"] or art["title"],
        "field": m["field"] or art["field"],
        "date": m["date"] or art["date"],
        "category_name": m["category_name"],
        "post_id": m["post_id"],
        "body": art["body"],
    }


def get_article_texts(ids: List[int]) -> List[Dict[str, str]]:
    """선택된 기사 id들의 전문을 읽어 반환(그래프 시드 문서용).

    반환: [{title, field, date, body, category_name, post_id}]
    """
    _, meta = _load()
    out = []
    for i in ids:
        try:
            m = meta[int(i)]
        except (IndexError, ValueError, TypeError):
            continue
        art = parse_article(m["path"])
        out.append({
            "title": m["title"] or art["title"],
            "field": m["field"],
            "date": m["date"],
            "category_name": m["category_name"],
            "post_id": m["post_id"],
            "body": art["body"],
        })
    return out

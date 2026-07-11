"""
本地 Zep 替代 —— 重排模型封装 (Qwen/Qwen3-Reranker-0.6B)

复刻 Zep search 的 reranker='cross_encoder'。对 (query, doc) 对打分（yes/no 概率），
用于对嵌入初排结果精排。懒加载单例，可用 LOCAL_GRAPH_RERANK_MODEL 覆盖，
设 LOCAL_GRAPH_RERANK_MODEL="" 可完全禁用重排。
"""

import os
import threading
from typing import List, Tuple

_DEFAULT_MODEL = os.environ.get("LOCAL_GRAPH_RERANK_MODEL", "Qwen/Qwen3-Reranker-0.6B")
_DEFAULT_INSTRUCT = "Given a search query, judge whether the document is relevant"

_PREFIX = ("<|im_start|>system\nJudge whether the Document meets the requirements based on the Query "
           "and the Instruct provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n"
           "<|im_start|>user\n")
_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

_lock = threading.Lock()
_state = {"tok": None, "model": None, "device": None, "true_id": None, "false_id": None}


def _resolve(provider, api_key, model):
    """provider 미지정 시 env(GRAPH_RERANK_PROVIDER) 기본."""
    prov = (provider or os.environ.get("GRAPH_RERANK_PROVIDER") or "local").lower()
    key = api_key or os.environ.get("VOYAGE_API_KEY")
    mdl = model or os.environ.get("VOYAGE_RERANK_MODEL", "rerank-2.5-lite")
    return prov, key, mdl


def enabled(provider: str = None, api_key: str = None) -> bool:
    """리랭커 사용 가능 여부. voyage면 키가 있으면 True, 로컬이면 모델 설정 여부."""
    prov, key, _ = _resolve(provider, api_key, None)
    if prov == "voyage":
        return bool(key)
    return bool(_DEFAULT_MODEL.strip())


def _load():
    if _state["model"] is not None:
        return
    with _lock:
        if _state["model"] is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        name = _DEFAULT_MODEL
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        tok = AutoTokenizer.from_pretrained(name, padding_side="left")
        model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=dtype).to(device).eval()
        _state.update(
            tok=tok, model=model, device=device,
            true_id=tok.convert_tokens_to_ids("yes"),
            false_id=tok.convert_tokens_to_ids("no"),
        )


def _format(instruction: str, query: str, doc: str) -> str:
    return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {doc}"


def score(query: str, docs: List[str], instruction: str = None,
          batch_size: int = 16, max_length: int = 1024) -> List[float]:
    """返回每个 doc 与 query 的相关性分数（0~1）。禁用时返回全 0。"""
    if not enabled() or not docs:
        return [0.0] * len(docs)
    _load()
    import torch

    tok, model, device = _state["tok"], _state["model"], _state["device"]
    instr = instruction or _DEFAULT_INSTRUCT
    texts = [_PREFIX + _format(instr, query, d) + _SUFFIX for d in docs]

    scores: List[float] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        enc = tok(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits[:, -1, :]
        true_v = logits[:, _state["true_id"]]
        false_v = logits[:, _state["false_id"]]
        pair = torch.stack([false_v, true_v], dim=1)
        prob = torch.nn.functional.log_softmax(pair, dim=1)[:, 1].exp()
        scores.extend(prob.cpu().float().tolist())
    return scores


def rerank(query: str, docs: List[str], top_k: int = None, instruction: str = None,
           provider: str = None, api_key: str = None, model: str = None) -> List[Tuple[int, float]]:
    """返回 [(原索引, 分数)]，按分数降序；top_k 截断。禁用时按原序返回。

    provider='voyage' 면 Voyage rerank API, 그 외(기본)는 로컬 Qwen.
    """
    prov, key, mdl = _resolve(provider, api_key, model)
    if not enabled(provider, api_key) or not docs:
        return [(i, 0.0) for i in range(len(docs))][: (top_k or len(docs))]
    if prov == "voyage":
        from . import voyage
        return voyage.rerank(query, docs, api_key=key, model=mdl, top_k=top_k)
    s = score(query, docs, instruction=instruction)
    order = sorted(range(len(docs)), key=lambda i: s[i], reverse=True)
    if top_k:
        order = order[:top_k]
    return [(i, s[i]) for i in order]

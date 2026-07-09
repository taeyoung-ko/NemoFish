"""
本地 Zep 替代 —— 嵌入模型封装 (Qwen/Qwen3-Embedding-0.6B)

在 nemofish 环境内直接用 transformers 加载（避开被 camel-oasis 钉死的 sentence-transformers==3.0.0）。
last-token 池化 + L2 归一化，输出可直接做余弦相似度。
懒加载单例：首次调用时才下载/加载模型（约 1.5GB 显存）。
"""

import os
import threading
from typing import List, Optional

import numpy as np

_DEFAULT_MODEL = os.environ.get("LOCAL_GRAPH_EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")
# 用于节点/边检索的默认指令（query 侧）
_DEFAULT_INSTRUCT = "Given a search query, retrieve relevant entities and facts from a knowledge graph"

_lock = threading.Lock()
_state = {"tok": None, "model": None, "device": None, "name": None}


def _load():
    if _state["model"] is not None:
        return
    with _lock:
        if _state["model"] is not None:
            return
        import torch
        from transformers import AutoModel, AutoTokenizer

        name = _DEFAULT_MODEL
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        tok = AutoTokenizer.from_pretrained(name, padding_side="left")
        model = AutoModel.from_pretrained(name, torch_dtype=dtype).to(device).eval()
        _state.update(tok=tok, model=model, device=device, name=name)


def _last_token_pool(last_hidden, attention_mask):
    import torch
    left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
    if left_padding:
        return last_hidden[:, -1]
    seq_len = attention_mask.sum(dim=1) - 1
    return last_hidden[torch.arange(last_hidden.shape[0], device=last_hidden.device), seq_len]


def embed(
    texts: List[str],
    is_query: bool = False,
    instruction: Optional[str] = None,
    batch_size: int = 16,
    max_length: int = 1024,
) -> np.ndarray:
    """返回 shape=(len(texts), dim) 的 L2 归一化向量。

    query 侧加检索指令（Qwen3-Embedding 推荐做法），文档侧不加。
    """
    if not texts:
        return np.zeros((0, 1024), dtype=np.float32)
    _load()
    import torch

    tok, model, device = _state["tok"], _state["model"], _state["device"]
    if is_query:
        instr = instruction or _DEFAULT_INSTRUCT
        texts = [f"Instruct: {instr}\nQuery:{t}" for t in texts]

    out_vecs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        enc = tok(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**enc)
        emb = _last_token_pool(outputs.last_hidden_state, enc["attention_mask"])
        emb = torch.nn.functional.normalize(emb, p=2, dim=1)
        out_vecs.append(emb.cpu().float().numpy())
    return np.concatenate(out_vecs, axis=0)


def embed_one(text: str, is_query: bool = False, instruction: Optional[str] = None) -> np.ndarray:
    return embed([text or ""], is_query=is_query, instruction=instruction)[0]


def cosine_topk(query_vec: np.ndarray, cand_vecs: np.ndarray, k: int) -> List[int]:
    """query_vec:(dim,), cand_vecs:(N,dim) 均已归一化。返回 top-k 的索引（降序）。"""
    if cand_vecs.shape[0] == 0:
        return []
    scores = cand_vecs @ query_vec
    k = min(k, len(scores))
    idx = np.argpartition(-scores, k - 1)[:k]
    return list(idx[np.argsort(-scores[idx])])

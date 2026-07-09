"""
本地 Zep 替代 —— 实体/关系抽取

复刻 Zep 的核心能力：把非结构化文本抽成知识图谱三元组。
复用 MiroFish 现有的 LLMClient（OpenAI 格式 → 指向 qwen36 上服务的 Qwen3.6-27B，
自动剥离 <think> 并走 JSON 模式），按图谱 ontology 约束抽取实体与关系。
"""

import json
from typing import Any, Dict, List

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger("mirofish.local_zep.extractor")

_SYSTEM = (
    "你是知识图谱抽取引擎。从给定文本中抽取实体(entities)和它们之间的关系(relations)。"
    "只输出 JSON，且严格符合给定的实体类型与关系类型约束。"
    "实体 name 用文本中的规范名称；relations 的 source/target 必须是 entities 中出现过的 name。"
    "若文本为韩语，name/summary/fact 保持韩语原文。"
)


def _ontology_hint(ontology: Dict[str, Any]) -> str:
    ets = ontology.get("entity_types", []) or []
    edts = ontology.get("edge_types", []) or []
    lines = []
    if ets:
        lines.append("允许的实体类型:")
        for e in ets:
            attrs = ", ".join(a["name"] for a in e.get("attributes", []))
            lines.append(f"  - {e['name']}: {e.get('description','')}" + (f" (属性: {attrs})" if attrs else ""))
    else:
        lines.append("实体类型: 不限（自行判断合理类型标签）")
    if edts:
        lines.append("允许的关系类型:")
        for e in edts:
            lines.append(f"  - {e['name']}: {e.get('description','')}")
    else:
        lines.append("关系类型: 不限")
    return "\n".join(lines)


def _prompt(text: str, ontology: Dict[str, Any]) -> str:
    return f"""{_ontology_hint(ontology)}

请从下面文本抽取知识图谱，输出 JSON，格式：
{{
  "entities": [
    {{"name": "实体名", "type": "实体类型标签", "summary": "对该实体的一句话概括", "attributes": {{}}}}
  ],
  "relations": [
    {{"source": "源实体名", "target": "目标实体名", "type": "关系类型名", "fact": "描述该关系的事实句", "attributes": {{}}}}
  ]
}}

文本：
\"\"\"
{text}
\"\"\"
"""


class Extractor:
    def __init__(self, llm: LLMClient = None):
        self._llm = llm

    @property
    def llm(self) -> LLMClient:
        # 懒初始化，避免 import 时就要求 LLM 配置
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def extract(self, text: str, ontology: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """返回 {"entities": [...], "relations": [...]}。失败时返回空结构。"""
        text = (text or "").strip()
        if not text:
            return {"entities": [], "relations": []}
        try:
            # 추출은 정형 작업 → Qwen3.6 non-thinking 모드로 호출(5~6배 빠름, 품질 영향 미미).
            # Qwen 권장 non-thinking 샘플링: temp=0.7, top_p=0.80, top_k=20, presence_penalty=1.5.
            # thinking OFF 시 <think> 블록이 안 나와 JSON 모드와도 충돌 없음.
            result = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _prompt(text, ontology)},
                ],
                temperature=0.7,
                max_tokens=4096,
                top_p=0.80,
                presence_penalty=1.5,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "top_k": 20,
                    "min_p": 0.0,
                },
            )
        except Exception as e:
            logger.warning(f"抽取失败，跳过该片段: {str(e)[:120]}")
            return {"entities": [], "relations": []}

        entities = result.get("entities") or []
        relations = result.get("relations") or []
        # 规范化：确保字段存在
        norm_entities = []
        for ent in entities:
            if not isinstance(ent, dict) or not ent.get("name"):
                continue
            norm_entities.append({
                "name": str(ent.get("name", "")).strip(),
                "type": str(ent.get("type", "Entity")).strip() or "Entity",
                "summary": str(ent.get("summary", "")).strip(),
                "attributes": ent.get("attributes") if isinstance(ent.get("attributes"), dict) else {},
            })
        norm_relations = []
        for rel in relations:
            if not isinstance(rel, dict) or not rel.get("source") or not rel.get("target"):
                continue
            norm_relations.append({
                "source": str(rel.get("source", "")).strip(),
                "target": str(rel.get("target", "")).strip(),
                "type": str(rel.get("type", "related_to")).strip() or "related_to",
                "fact": str(rel.get("fact", "")).strip(),
                "attributes": rel.get("attributes") if isinstance(rel.get("attributes"), dict) else {},
            })
        return {"entities": norm_entities, "relations": norm_relations}

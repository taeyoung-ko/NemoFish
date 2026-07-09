"""
本地 Zep 替代 —— 数据类型与返回对象

复刻 zep_cloud 中被 MiroFish 使用的类型和对象字段，使调用方无需修改即可工作。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class InternalServerError(Exception):
    """复刻 zep_cloud.InternalServerError，供 zep_paging 重试逻辑捕获。"""
    pass


@dataclass
class EpisodeData:
    """复刻 zep_cloud.EpisodeData：graph.add_batch 的输入单元。"""
    data: str
    type: str = "text"


@dataclass
class EntityEdgeSourceTarget:
    """复刻 zep_cloud.EntityEdgeSourceTarget：边的 source/target 约束。"""
    source: str = "Entity"
    target: str = "Entity"


class _AttrObj:
    """轻量属性袋对象，模拟 Zep SDK 返回的 node/edge/episode 对象。

    调用方通过 getattr(obj, 'uuid_') / obj.name / obj.fact 等访问，
    这里用普通属性满足它们。
    """

    def __init__(self, **kwargs: Any):
        self.__dict__.update(kwargs)

    def __repr__(self) -> str:
        return f"_AttrObj({self.__dict__})"


def make_node(
    uuid: str,
    name: str = "",
    labels: Optional[List[str]] = None,
    summary: str = "",
    attributes: Optional[Dict[str, Any]] = None,
) -> _AttrObj:
    """构造符合 zep_entity_reader / zep_tools 期望字段的节点对象。"""
    return _AttrObj(
        uuid_=uuid,
        uuid=uuid,
        name=name or "",
        labels=labels or [],
        summary=summary or "",
        attributes=attributes or {},
    )


def make_edge(
    uuid: str,
    name: str = "",
    fact: str = "",
    source_node_uuid: str = "",
    target_node_uuid: str = "",
    attributes: Optional[Dict[str, Any]] = None,
) -> _AttrObj:
    """构造符合调用方期望字段的边对象。"""
    return _AttrObj(
        uuid_=uuid,
        uuid=uuid,
        name=name or "",
        fact=fact or "",
        source_node_uuid=source_node_uuid or "",
        target_node_uuid=target_node_uuid or "",
        attributes=attributes or {},
    )


def make_episode(uuid: str, processed: bool = True) -> _AttrObj:
    """构造 episode 对象。本地提取是同步的，故 processed 恒为 True。"""
    return _AttrObj(uuid_=uuid, uuid=uuid, processed=processed)


@dataclass
class SearchResult:
    """复刻 graph.search 的返回：调用方读取 .edges / .nodes。"""
    edges: List[_AttrObj] = field(default_factory=list)
    nodes: List[_AttrObj] = field(default_factory=list)

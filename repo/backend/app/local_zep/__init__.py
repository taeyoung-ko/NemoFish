"""
local_zep —— zep_cloud 的本地 drop-in 替代包

用法（替换原 import）：
  from zep_cloud.client import Zep                    -> from ..local_zep import Zep
  from zep_cloud import EpisodeData, EntityEdgeSourceTarget, InternalServerError
                                                      -> from ..local_zep import ...
  from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel
                                                      -> from ..local_zep.ontology import ...

后端：抽取=服务中的 Qwen3.6-27B(HTTP)，嵌入/重排=本地 Qwen 0.6B，存储=SQLite。
"""

from .client import Zep
from .models import EntityEdgeSourceTarget, EpisodeData, InternalServerError
from .ontology import EdgeModel, EntityModel, EntityText

__all__ = [
    "Zep",
    "EpisodeData",
    "EntityEdgeSourceTarget",
    "InternalServerError",
    "EntityModel",
    "EntityText",
    "EdgeModel",
]

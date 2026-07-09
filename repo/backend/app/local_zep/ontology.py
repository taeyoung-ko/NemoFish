"""
本地 Zep 替代 —— 本体基类

复刻 zep_cloud.external_clients.ontology 的 EntityModel / EntityText / EdgeModel。
graph_builder.py 会用 `type(name, (EntityModel,), attrs)` 动态创建 pydantic 子类，
并给字段加 `Optional[EntityText]` 注解和 `Field(description=..., default=None)`。

因此：
- EntityText 必须是一个可作为 pydantic 字段类型的类型（这里用 str 子类）
- EntityModel / EdgeModel 必须是 pydantic BaseModel，且允许额外字段
"""

from pydantic import BaseModel, ConfigDict


class EntityText(str):
    """标记类型：表示实体的文本属性。作为 str 子类，可直接用于 pydantic 注解。"""
    pass


class EntityModel(BaseModel):
    """实体本体基类。允许动态添加任意属性字段，并接受 EntityText 等自定义类型注解。"""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class EdgeModel(BaseModel):
    """边本体基类。允许动态添加任意属性字段。"""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


def introspect_entity_types(entities) -> list:
    """将 {name: EntityModelSubclass} 还原为普通 dict 列表。

    返回: [{"name": str, "description": str, "attributes": [{"name","description"}]}]
    """
    result = []
    if not entities:
        return result
    for name, cls in entities.items():
        attrs = []
        # pydantic v2: model_fields 保存字段名与 FieldInfo（含 description）
        for fname, finfo in getattr(cls, "model_fields", {}).items():
            attrs.append({
                "name": fname,
                "description": getattr(finfo, "description", "") or fname,
            })
        result.append({
            "name": name,
            "description": (cls.__doc__ or f"A {name} entity.").strip(),
            "attributes": attrs,
        })
    return result


def introspect_edge_types(edges) -> list:
    """将 {name: (EdgeModelSubclass, [EntityEdgeSourceTarget])} 还原为普通 dict 列表。

    返回: [{"name","description","attributes":[...],"source_targets":[{"source","target"}]}]
    """
    result = []
    if not edges:
        return result
    for name, value in edges.items():
        if isinstance(value, (tuple, list)) and len(value) >= 1:
            cls = value[0]
            source_targets = value[1] if len(value) > 1 else []
        else:
            cls, source_targets = value, []
        attrs = []
        for fname, finfo in getattr(cls, "model_fields", {}).items():
            attrs.append({
                "name": fname,
                "description": getattr(finfo, "description", "") or fname,
            })
        st_list = []
        for st in (source_targets or []):
            st_list.append({
                "source": getattr(st, "source", "Entity"),
                "target": getattr(st, "target", "Entity"),
            })
        result.append({
            "name": name,
            "description": (cls.__doc__ or f"A {name} relationship.").strip(),
            "attributes": attrs,
            "source_targets": st_list,
        })
    return result

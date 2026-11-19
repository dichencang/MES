"""Idempotent reference data for the basic-data module."""

from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import insert

from app.models import system as m

MENUS = (
    ("material", "物料档案", "Box", 40, ("新建物料", "编辑物料", "启停用物料")),
    ("process", "工序档案", "Operation", 50, ("新建工序", "编辑工序", "启停用工序")),
    ("bom", "产品 BOM", "Share", 60, ("查看 BOM 版本", "新建/复制 BOM", "保存 BOM 草稿", "发布 BOM", "删除 BOM 草稿")),
    ("routing", "工艺路线", "Guide", 70, ("查看工艺路线版本", "新建/复制工艺路线", "保存工艺路线草稿", "发布工艺路线", "删除工艺路线草稿")),
)
ARCHIVE_ACTIONS = ("create", "update", "set-status")
VERSION_ACTIONS = ("query", "create", "update", "publish", "delete")
DICTIONARIES = {
    "material_category": ("物料类别", (("成品", "FINISHED"), ("半成品", "SEMI"), ("原材料", "RAW"))),
    "material_unit": ("计量单位", (("个", "PCS"), ("台", "SET"), ("千克", "KG"), ("米", "M"), ("升", "L"), ("件", "PIECE"))),
}


def permission_insert(parent_code, code, name, node_type, order, *, path=None, component=None, icon=None):
    permission = m.permission
    values = (code, name, node_type, order, path, component, icon)
    return insert(permission).from_select(
        ("parent_id", "permission_code", "perm_name", "perm_type", "order_num", "path", "component", "icon"),
        select(permission.c.id, *(literal(value) for value in values))
        .where(permission.c.permission_code == parent_code),
    ).on_conflict_do_nothing(index_elements=[permission.c.permission_code])


def seed_statements():
    for resource, name, icon, order, buttons in MENUS:
        prefix = f"basic:{resource}"
        menu = f"{prefix}:list"
        yield permission_insert(
            "basic", menu, name, "MENU", order,
            path=f"/basic/{resource}", component=f"basic/{resource}/index", icon=icon,
        )
        actions = ARCHIVE_ACTIONS if resource in ("material", "process") else VERSION_ACTIONS
        for position, (action, label) in enumerate(zip(actions, buttons, strict=True), 1):
            yield permission_insert(menu, f"{prefix}:{action}", label, "BUTTON", position)

    for code, (name, items) in DICTIONARIES.items():
        yield insert(m.dict_type).values(dict_code=code, dict_name=name).on_conflict_do_nothing(
            index_elements=[m.dict_type.c.dict_code]
        )
        yield insert(m.dict_data).values([
            dict(dict_code=code, dict_label=label, dict_value=value, order_num=position)
            for position, (label, value) in enumerate(items, 1)
        ]).on_conflict_do_nothing(index_elements=[m.dict_data.c.dict_code, m.dict_data.c.dict_value])

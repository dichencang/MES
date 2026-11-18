from sqlalchemy import select

from app.models import system as m
from app.services.auth import roles_for_user


async def granted_permissions(db, user_id):
    roles = await roles_for_user(db, user_id)
    is_super = any(role["is_super"] == "1" for role in roles)
    statement = select(m.permission).where(m.permission.c.status == "0")
    if not is_super:
        grants = select(m.role_permission.c.permission_id).where(
            m.role_permission.c.role_id.in_([role["id"] for role in roles]),
        )
        statement = statement.where(m.permission.c.id.in_(grants))
    return (await db.execute(statement.order_by(
        m.permission.c.order_num, m.permission.c.id,
    ))).mappings().all()


def navigation_tree(rows):
    menus = {}
    for row in rows:
        if row["perm_type"] == "MENU" and row["visible"] == "0":
            menus.setdefault(row["parent_id"], []).append(node(row, []))
    tree = []
    for row in rows:
        if row["visible"] != "0":
            continue
        if row["perm_type"] == "MENU" and row["parent_id"] == 0:
            tree.append(node(row, []))
        elif row["perm_type"] == "DIR" and row["id"] in menus:
            tree.append(node(row, menus[row["id"]]))
    return tree


def node(row, children):
    return {
        "id": str(row["id"]), "parentId": str(row["parent_id"]),
        "permName": row["perm_name"], "permType": row["perm_type"],
        "permissionCode": row["permission_code"], "path": row["path"],
        "component": row["component"], "icon": row["icon"],
        "orderNum": row["order_num"], "visible": row["visible"], "children": children,
    }

import re
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import system as m
from app.services.auth import revoke_user_sessions, roles_for_user
from app.services.management import data_filter, existing
from app.utils.passwords import hash_password
from app.utils.responses import ApiError


def invalid(message):
    return ApiError(400, 1001, message)


def protected():
    return ApiError(409, 1005, "内置资源受保护")


def conflict(message):
    return ApiError(409, 1003, message)


def values(body, *, exclude=(), partial=False):
    data = body.model_dump(exclude=set(exclude), exclude_unset=partial)
    for field in ("phone", "email", "leader", "remark", "icon", "path", "component"):
        if field in data and data[field] is not None and not data[field].strip():
            data[field] = None
    for field in ("dept_id", "parent_id"):
        if field in data:
            data[field] = int(data[field])
    return data


async def commit(db):
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise integrity_error(error) from error


def integrity_error(error):
    if error.orig.sqlstate == "23505":
        return ApiError(409, 1004, "记录已存在")
    if error.orig.sqlstate == "23503":
        return conflict("记录存在引用关系")
    return invalid("数据不符合字段约束")


async def record(db, table, id, *, lock=False):
    if lock:
        row = (await db.execute(select(table).where(table.c.id == id).with_for_update())).mappings().one_or_none()
        if row is None:
            raise ApiError(404, 1002, "记录不存在")
        return row
    return await existing(db, table, id)


async def target_user(db, id, actor, operation):
    row = await record(db, m.user, id, lock=True)
    if row["del_flag"] == "1":
        raise ApiError(404, 1002, "用户不存在")
    if row["is_builtin"] == "1":
        raise protected()
    account = await existing(db, m.user, actor)
    scope = await data_filter(db, account, f"system:user:{operation}", m.user.c.dept_id, m.user.c.create_by)
    if await db.scalar(select(m.user.c.id).where(m.user.c.id == id, scope)) is None:
        raise ApiError(403, 3001, "无权操作该用户")
    target_roles = await roles_for_user(db, id)
    if any(role["is_super"] == "1" for role in target_roles):
        if not await is_super(db, actor):
            raise protected()
    return row


async def is_super(db, user_id):
    return any(row["is_super"] == "1" for row in await roles_for_user(db, user_id))


async def validate_department(db, dept_id):
    if await db.scalar(select(m.dept.c.id).where(m.dept.c.id == dept_id, m.dept.c.status == "0")) is None:
        raise invalid("请选择正常部门")


async def validate_roles(db, ids, actor):
    selected = (await db.execute(select(m.role).where(m.role.c.id.in_(ids)))).mappings().all()
    if len(selected) != len(ids):
        raise invalid("角色不存在")
    if any(row["is_super"] == "1" for row in selected) and not await is_super(db, actor):
        raise protected()


async def replace_links(db, table, key, id, other_key, ids):
    await db.execute(table.delete().where(table.c[key] == id))
    if ids:
        await db.execute(table.insert(), [{key: id, other_key: value} for value in ids])


def unique_ids(values):
    return list(dict.fromkeys(map(int, values)))


async def create_user(db, body, actor):
    data = values(body, exclude=("password", "role_ids"))
    await validate_department(db, data["dept_id"])
    ids = unique_ids(body.role_ids)
    await validate_roles(db, ids, actor)
    id = await db.scalar(m.user.insert().values(
        **data, password_hash=await hash_password(body.password), create_by=actor, update_by=actor,
    ).returning(m.user.c.id))
    await replace_links(db, m.user_role, "user_id", id, "role_id", ids)


async def update_user(db, id, actor, data):
    await db.execute(m.user.update().where(m.user.c.id == id).values(
        **data, update_by=actor, update_time=datetime.now(UTC),
    ))


async def edit_user(db, id, body, actor):
    row = await target_user(db, id, actor, "update")
    data = values(body)
    if row["dept_id"] != data["dept_id"]:
        await validate_department(db, data["dept_id"])
    await update_user(db, id, actor, data)


async def delete_user(db, id, actor):
    await target_user(db, id, actor, "delete")
    await update_user(db, id, actor, {"del_flag": "1"})
    await revoke_user_sessions(db, id)


async def reset_password(db, id, body, actor):
    await target_user(db, id, actor, "reset-password")
    await update_user(db, id, actor, {"password_hash": await hash_password(body.password)})
    await revoke_user_sessions(db, id)


async def set_user_status(db, id, body, actor):
    await target_user(db, id, actor, "set-status")
    await update_user(db, id, actor, {"status": body.status})
    if body.status == "1":
        await revoke_user_sessions(db, id)


async def assign_user_roles(db, id, body, actor):
    await target_user(db, id, actor, "assign-roles")
    ids = unique_ids(body.role_ids)
    await validate_roles(db, ids, actor)
    await replace_links(db, m.user_role, "user_id", id, "role_id", ids)
    await update_user(db, id, actor, {})


async def target_role(db, id):
    row = await record(db, m.role, id, lock=True)
    if row["is_super"] == "1":
        raise protected()


async def set_scope(db, id, body):
    ids = unique_ids(body.dept_ids) if body.data_scope == "CUSTOM" else []
    if body.data_scope == "CUSTOM":
        count = len((await db.scalars(select(m.dept.c.id).where(m.dept.c.id.in_(ids)))).all())
        if not ids or count != len(ids):
            raise invalid("自定义数据范围需要选择有效部门")
    await db.execute(m.role.update().where(m.role.c.id == id).values(
        data_scope=body.data_scope, update_time=datetime.now(UTC),
    ))
    await replace_links(db, m.role_dept, "role_id", id, "dept_id", ids)


async def create_role(db, body):
    id = await db.scalar(m.role.insert().values(**values(body, exclude=("dept_ids",)))
                         .returning(m.role.c.id))
    await set_scope(db, id, body)


async def assign_permissions(db, id, body, actor):
    await target_role(db, id)
    ids = unique_ids(body.permission_ids)
    records = (await db.execute(select(m.permission).where(m.permission.c.id.in_(ids)))).mappings().all()
    if len(records) != len(ids):
        raise invalid("权限节点不存在")
    if not await is_super(db, actor):
        from app.services.permissions import granted_permissions

        granted = {row["id"] for row in await granted_permissions(db, actor)}
        if not set(ids).issubset(granted):
            raise ApiError(403, 3001, "不能授予自身未拥有的权限")
    await replace_links(db, m.role_permission, "role_id", id, "permission_id", ids)


async def delete_role(db, id):
    await target_role(db, id)
    if await db.scalar(select(m.user_role.c.user_id).where(m.user_role.c.role_id == id).limit(1)):
        raise conflict("角色已分配给用户")
    await replace_links(db, m.role_permission, "role_id", id, "permission_id", [])
    await replace_links(db, m.role_dept, "role_id", id, "dept_id", [])
    await db.execute(m.role.delete().where(m.role.c.id == id))


async def validate_tree(db, table, parent_id, id):
    await db.execute(text(f"LOCK TABLE {table.name} IN SHARE ROW EXCLUSIVE MODE"))
    parent = None
    current = parent_id
    while current:
        if current == id:
            raise invalid("上级节点不能是自身或其子节点")
        row = await existing(db, table, current)
        if parent is None:
            parent = row
        current = row["parent_id"]
    return parent


async def save_node(db, table, body, id=None):
    data = values(body)
    parent = await validate_tree(db, table, data["parent_id"], id)
    if id is not None:
        old = await existing(db, table, id)
    if table is m.permission:
        code = data.get("permission_code") if id is None else old["permission_code"]
        kind = data["perm_type"]
        parent_type = {"DIR": None, "MENU": "DIR", "BUTTON": "MENU"}[kind]
        if (parent["perm_type"] if parent else None) != parent_type:
            raise invalid("权限层级无效")
        expected = (re.escape(parent["permission_code"]) + ":" if parent else "") + r"[a-z0-9]+(?:-[a-z0-9]+)*"
        if not re.fullmatch(expected, code):
            raise invalid("权限编码与层级不匹配")
        if kind == "MENU" and (not (data["path"] or "").startswith("/") or not data["component"]):
            raise invalid("菜单须填写绝对路由和组件路径")
        if kind == "BUTTON":
            data.update(path=None, component=None, icon=None)
    if id is None:
        await db.execute(table.insert().values(**data))
    else:
        await update_row(db, table, id, data)


async def update_row(db, table, id, data):
    await existing(db, table, id)
    if "update_time" in table.c:
        data["update_time"] = datetime.now(UTC)
    await db.execute(table.update().where(table.c.id == id).values(**data))


async def delete_row(db, table, id):
    if "parent_id" in table.c:
        await db.execute(text(f"LOCK TABLE {table.name} IN SHARE ROW EXCLUSIVE MODE"))
        if await db.scalar(select(table.c.id).where(table.c.parent_id == id).limit(1)):
            raise conflict("请先移除子节点")
    row = await existing(db, table, id)
    if table is m.config and row["config_type"] == "0":
        raise protected()
    await db.execute(table.delete().where(table.c.id == id))

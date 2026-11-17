from datetime import datetime, timedelta, timezone

from sqlalchemy import false, func, or_, select, true

from app.models import system as m
from app.services.auth import roles_for_user
from app.services.permissions import granted_permissions
from app.utils.responses import ApiError

CHINA_TIME = timezone(timedelta(hours=8))


def camel(name):
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


def serialize(row, fields):
    result = {}
    for field in fields.split():
        value = row[field]
        if value is not None and (field == "id" or field.endswith("_id")):
            value = str(value)
        if isinstance(value, datetime):
            value = value.astimezone(CHINA_TIME).isoformat()
        result[camel(field)] = value
    return result


async def require(db, account, code):
    roles = await roles_for_user(db, account["id"])
    if any(role["is_super"] == "1" for role in roles):
        return
    permissions = await granted_permissions(db, account["id"])
    if not any(row["permission_code"] == code for row in permissions):
        raise ApiError(403, 3001, "无权执行此操作")


async def data_filter(db, account, code, dept_column, owner_column):
    roles = await roles_for_user(db, account["id"])
    if any(role["is_super"] == "1" for role in roles):
        return true()
    grants = select(m.role_permission.c.role_id).join(m.permission).where(
        m.permission.c.permission_code == code, m.permission.c.status == "0",
    )
    permitted = set(await db.scalars(grants))
    roles = [role for role in roles if role["id"] in permitted]
    conditions = []
    for role in roles:
        scope = role["data_scope"]
        if scope == "ALL":
            return true()
        if scope == "SELF":
            conditions.append(owner_column == account["id"])
        elif scope == "DEPT":
            conditions.append(dept_column == account["dept_id"])
        elif scope == "CUSTOM":
            departments = select(m.role_dept.c.dept_id).where(m.role_dept.c.role_id == role["id"])
            conditions.append(dept_column.in_(departments))
        elif scope == "DEPT_CHILD":
            department = m.dept.c
            subtree = select(department.id).where(department.id == account["dept_id"]).cte(recursive=True)
            subtree = subtree.union(select(department.id).join(subtree, department.parent_id == subtree.c.id))
            conditions.append(dept_column.in_(select(subtree.c.id)))
    return or_(false(), *conditions)


async def rows(db, statement):
    return (await db.execute(statement)).mappings().all()


async def pagination(db, statement, page, size):
    total = await db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    records = await rows(db, statement.offset((page - 1) * size).limit(size))
    return total, records


def filters(statement, *, exact=(), fuzzy=()):
    for column, value in exact:
        if value is not None:
            statement = statement.where(column == value)
    for column, value in fuzzy:
        if value:
            statement = statement.where(column.icontains(value, autoescape=True))
    return statement


async def existing(db, table, id):
    row = (await db.execute(select(table).where(table.c.id == id))).mappings().one_or_none()
    if row is None:
        raise ApiError(404, 1002, "记录不存在")
    return row


def tree(records, fields):
    nodes = {row["id"]: dict(serialize(row, fields), children=[]) for row in records}
    roots = []
    for row in records:
        node = nodes[row["id"]]
        if row["parent_id"] == 0:
            roots.append(node)
        elif row["parent_id"] in nodes:
            nodes[row["parent_id"]]["children"].append(node)
    return roots

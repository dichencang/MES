from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import AwareDatetime
from sqlalchemy import select

from app.models import system as m
from app.dto.management import Id as ResourceId
from app.routers.auth import Account, Db
from app.services.management import data_filter, existing, filters, pagination, require, rows, serialize, tree
from app.utils.responses import ApiError, success

router = APIRouter(tags=["系统管理"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Status = Literal["0", "1"]
DICT_FIELDS = "id dict_code dict_label dict_value order_num status"
LOG_FIELDS = "id operator_id operator_name module operation request_url ip status cost_time oper_time"


async def log_scope(db, account, operation):
    operator_dept = select(m.user.c.dept_id).where(
        m.user.c.id == m.oper_log.c.operator_id,
    ).scalar_subquery()
    return await data_filter(db, account, operation, operator_dept, m.oper_log.c.operator_id)


async def page_data(db, statement, page, size, fields):
    total, records = await pagination(db, statement, page, size)
    return {"total": total, "list": [serialize(row, fields) for row in records]}


@router.get("/users")
async def users(db: Db, account: Account, page: Page = 1, pageSize: PageSize = 10,
                username: str | None = None, realName: str | None = None,
                deptId: ResourceId | None = None, status: Status | None = None):
    await require(db, account, "system:user")
    u = m.user.c
    scope = await data_filter(db, account, "system:user", u.dept_id, u.create_by)
    statement = select(m.user, m.dept.c.dept_name).join(m.dept).where(u.del_flag == "0", scope)
    statement = filters(statement, exact=((u.dept_id, int(deptId) if deptId else None), (u.status, status)),
                        fuzzy=((u.username, username), (u.real_name, realName)))
    total, records = await pagination(db, statement.order_by(u.create_time.desc(), u.id.desc()), page, pageSize)
    links = await rows(db, select(m.user_role.c.user_id, m.role).join(m.role).where(
        m.user_role.c.user_id.in_([row["id"] for row in records]),
    ).order_by(m.role.c.id))
    by_user = {}
    for link in links:
        by_user.setdefault(link["user_id"], []).append(serialize(link, "id role_code role_name"))
    fields = "id username real_name dept_id dept_name phone email status is_builtin create_time"
    return success({"total": total, "list": [
        dict(serialize(row, fields), roles=by_user.get(row["id"], [])) for row in records
    ]})


@router.get("/roles")
async def roles(db: Db, account: Account, page: Page = 1, pageSize: PageSize = 10,
                roleName: str | None = None, roleCode: str | None = None):
    await require(db, account, "system:role")
    r = m.role.c
    statement = filters(select(m.role), fuzzy=((r.role_name, roleName), (r.role_code, roleCode)))
    total, records = await pagination(db, statement.order_by(r.create_time, r.id), page, pageSize)
    links = await rows(db, select(m.role_dept).where(
        m.role_dept.c.role_id.in_([row["id"] for row in records if row["data_scope"] == "CUSTOM"]),
    ).order_by(m.role_dept.c.dept_id))
    by_role = {}
    for link in links:
        by_role.setdefault(link["role_id"], []).append(str(link["dept_id"]))
    fields = "id role_code role_name data_scope is_super remark create_time"
    return success({"total": total, "list": [
        dict(serialize(row, fields), deptIds=by_role.get(row["id"], [])) for row in records
    ]})


@router.get("/roles/{id}/permissions")
async def role_permissions(id: ResourceId, db: Db, account: Account):
    await require(db, account, "system:role:query")
    await existing(db, m.role, int(id))
    ids = await db.scalars(select(m.role_permission.c.permission_id).where(
        m.role_permission.c.role_id == int(id),
    ).order_by(m.role_permission.c.permission_id))
    return success({"permissionIds": [str(value) for value in ids]})


async def read_tree(db, table, include_disabled, fields):
    statement = select(table).order_by(table.c.order_num, table.c.id)
    if not include_disabled:
        statement = statement.where(table.c.status == "0")
    return success(tree(await rows(db, statement), fields))


@router.get("/depts/tree")
async def departments(db: Db, account: Account, includeDisabled: bool = False):
    await require(db, account, "system:dept")
    return await read_tree(db, m.dept, includeDisabled, "id parent_id dept_name order_num leader phone status")


@router.get("/permissions/tree")
async def permissions(db: Db, account: Account, includeDisabled: bool = False):
    await require(db, account, "system:permission")
    return await read_tree(db, m.permission, includeDisabled,
        "id parent_id perm_name perm_type permission_code path component icon order_num visible status")


@router.get("/dict-types")
async def dictionary_types(db: Db, account: Account, page: Page = 1, pageSize: PageSize = 10,
                           dictName: str | None = None, dictCode: str | None = None,
                           status: Status | None = None):
    await require(db, account, "system:dict")
    d = m.dict_type.c
    statement = filters(select(m.dict_type), exact=((d.status, status),),
                        fuzzy=((d.dict_name, dictName), (d.dict_code, dictCode)))
    return success(await page_data(db, statement.order_by(d.id), page, pageSize,
                                   "id dict_code dict_name status remark"))


@router.get("/dict-data")
async def dictionary_items(dictCode: Annotated[str, Query(min_length=1)], db: Db, account: Account):
    await require(db, account, "system:dict")
    d = m.dict_data.c
    records = await rows(db, select(m.dict_data).where(d.dict_code == dictCode).order_by(d.order_num, d.id))
    return success([serialize(row, DICT_FIELDS) for row in records])


@router.get("/configs")
async def configs(db: Db, account: Account, page: Page = 1, pageSize: PageSize = 10,
                  configName: str | None = None, configKey: str | None = None,
                  configType: Status | None = None):
    await require(db, account, "system:config")
    c = m.config.c
    statement = filters(select(m.config), exact=((c.config_type, configType),),
                        fuzzy=((c.config_name, configName), (c.config_key, configKey)))
    return success(await page_data(db, statement.order_by(c.id), page, pageSize,
                                   "id config_name config_key config_value config_type remark"))


@router.get("/oper-logs")
async def logs(db: Db, account: Account, page: Page = 1, pageSize: PageSize = 10,
               operatorName: str | None = None, module: str | None = None,
               status: Status | None = None, startTime: AwareDatetime | None = None,
               endTime: AwareDatetime | None = None):
    await require(db, account, "system:oper-log")
    c = m.oper_log.c
    scope = await log_scope(db, account, "system:oper-log")
    statement = filters(select(m.oper_log).where(scope), exact=((c.module, module), (c.status, status)),
                        fuzzy=((c.operator_name, operatorName),))
    if startTime is not None:
        statement = statement.where(c.oper_time >= startTime)
    if endTime is not None:
        statement = statement.where(c.oper_time < endTime)
    return success(await page_data(db, statement.order_by(c.oper_time.desc(), c.id.desc()),
                                   page, pageSize, LOG_FIELDS))


@router.get("/oper-logs/{id}")
async def log_detail(id: ResourceId, db: Db, account: Account):
    await require(db, account, "system:oper-log:query")
    scope = await log_scope(db, account, "system:oper-log:query")
    records = await rows(db, select(m.oper_log).where(m.oper_log.c.id == int(id), scope))
    if not records:
        raise ApiError(404, 1002, "操作日志不存在")
    row = records[0]
    return success(serialize(row, LOG_FIELDS + " method request_param error_msg"))

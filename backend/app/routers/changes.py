from fastapi import APIRouter, Request
from sqlalchemy import text

from app.dto import management as dto
from app.models import system as m
from app.routers.auth import Account, Db
from app.services import changes
from app.services.audit import AuditRoute, write_log
from app.services.management import require
from app.utils.responses import success

router = APIRouter(tags=["系统管理"], route_class=AuditRoute)



@router.post("/users")
async def create_user(body: dto.UserCreate, db: Db, account: Account):
    await require(db, account, "system:user:create")
    await changes.create_user(db, body, account["id"])
    await changes.commit(db)
    return success()


@router.put("/users/{id}")
async def edit_user(id: dto.Id, body: dto.UserEdit, db: Db, account: Account):
    await require(db, account, "system:user:update")
    await changes.edit_user(db, int(id), body, account["id"])
    await changes.commit(db)
    return success()


@router.delete("/users/{id}")
async def delete_user(id: dto.Id, db: Db, account: Account):
    await require(db, account, "system:user:delete")
    await changes.delete_user(db, int(id), account["id"])
    await changes.commit(db)
    return success()


@router.put("/users/{id}/password")
async def reset_password(id: dto.Id, body: dto.PasswordReset, db: Db, account: Account):
    await require(db, account, "system:user:reset-password")
    await changes.reset_password(db, int(id), body, account["id"])
    await changes.commit(db)
    return success()


@router.put("/users/{id}/status")
async def set_user_status(id: dto.Id, body: dto.Status, db: Db, account: Account):
    await require(db, account, "system:user:set-status")
    await changes.set_user_status(db, int(id), body, account["id"])
    await changes.commit(db)
    return success()


@router.put("/users/{id}/roles")
async def assign_user_roles(id: dto.Id, body: dto.UserRoles, db: Db, account: Account):
    await require(db, account, "system:user:assign-roles")
    await changes.assign_user_roles(db, int(id), body, account["id"])
    await changes.commit(db)
    return success()


@router.post("/roles")
async def create_role(body: dto.RoleCreate, db: Db, account: Account):
    await require(db, account, "system:role:create")
    await changes.create_role(db, body)
    await changes.commit(db)
    return success()


@router.put("/roles/{id}")
async def edit_role(id: dto.Id, body: dto.RoleEdit, db: Db, account: Account):
    await require(db, account, "system:role:update")
    await changes.target_role(db, int(id))
    await changes.update_row(db, m.role, int(id), changes.values(body))
    await changes.commit(db)
    return success()


@router.delete("/roles/{id}")
async def delete_role(id: dto.Id, db: Db, account: Account):
    await require(db, account, "system:role:delete")
    await changes.delete_role(db, int(id))
    await changes.commit(db)
    return success()


@router.put("/roles/{id}/permissions")
async def assign_permissions(id: dto.Id, body: dto.RolePermissions, db: Db, account: Account):
    await require(db, account, "system:role:assign-permissions")
    await changes.assign_permissions(db, int(id), body, account["id"])
    await changes.commit(db)
    return success()


@router.put("/roles/{id}/data-scope")
async def set_data_scope(id: dto.Id, body: dto.DataScope, db: Db, account: Account):
    await require(db, account, "system:role:set-data-scope")
    await changes.target_role(db, int(id))
    await changes.set_scope(db, int(id), body)
    await changes.commit(db)
    return success()


@router.post("/permissions")
async def create_permission(body: dto.PermissionCreate, db: Db, account: Account):
    await require(db, account, "system:permission:create")
    await changes.save_node(db, m.permission, body)
    await changes.commit(db)
    return success()


@router.put("/permissions/{id}")
async def edit_permission(id: dto.Id, body: dto.PermissionEdit, db: Db, account: Account):
    await require(db, account, "system:permission:update")
    await changes.save_node(db, m.permission, body, int(id))
    await changes.commit(db)
    return success()


@router.delete("/permissions/{id}")
async def delete_permission(id: dto.Id, db: Db, account: Account):
    await require(db, account, "system:permission:delete")
    await changes.delete_row(db, m.permission, int(id))
    await changes.commit(db)
    return success()


@router.post("/depts")
async def create_dept(body: dto.Department, db: Db, account: Account):
    await require(db, account, "system:dept:create")
    await changes.save_node(db, m.dept, body)
    await changes.commit(db)
    return success()


@router.put("/depts/{id}")
async def edit_dept(id: dto.Id, body: dto.Department, db: Db, account: Account):
    await require(db, account, "system:dept:update")
    await changes.save_node(db, m.dept, body, int(id))
    await changes.commit(db)
    return success()


@router.delete("/depts/{id}")
async def delete_dept(id: dto.Id, db: Db, account: Account):
    await require(db, account, "system:dept:delete")
    await changes.delete_row(db, m.dept, int(id))
    await changes.commit(db)
    return success()


@router.post("/dict-types")
async def create_dict_type(body: dto.DictTypeCreate, db: Db, account: Account):
    await require(db, account, "system:dict:type-create")
    await db.execute(m.dict_type.insert().values(**changes.values(body)))
    await changes.commit(db)
    return success()


@router.put("/dict-types/{id}")
async def edit_dict_type(id: dto.Id, body: dto.DictTypeEdit, db: Db, account: Account):
    await require(db, account, "system:dict:type-update")
    await changes.update_row(db, m.dict_type, int(id), changes.values(body))
    await changes.commit(db)
    return success()


@router.delete("/dict-types/{id}")
async def delete_dict_type(id: dto.Id, db: Db, account: Account):
    await require(db, account, "system:dict:type-delete")
    await changes.delete_row(db, m.dict_type, int(id))
    await changes.commit(db)
    return success()


@router.post("/dict-data")
async def create_dict_data(body: dto.DictItemCreate, db: Db, account: Account):
    await require(db, account, "system:dict:item-create")
    await db.execute(m.dict_data.insert().values(**changes.values(body)))
    await changes.commit(db)
    return success()


@router.put("/dict-data/{id}")
async def edit_dict_data(id: dto.Id, body: dto.DictItemEdit, db: Db, account: Account):
    await require(db, account, "system:dict:item-update")
    await changes.update_row(db, m.dict_data, int(id), changes.values(body))
    await changes.commit(db)
    return success()


@router.delete("/dict-data/{id}")
async def delete_dict_data(id: dto.Id, db: Db, account: Account):
    await require(db, account, "system:dict:item-delete")
    await changes.delete_row(db, m.dict_data, int(id))
    await changes.commit(db)
    return success()


@router.post("/configs")
async def create_config(body: dto.ConfigCreate, db: Db, account: Account):
    await require(db, account, "system:config:create")
    await db.execute(m.config.insert().values(**changes.values(body)))
    await changes.commit(db)
    return success()


@router.put("/configs/{id}")
async def edit_config(id: dto.Id, body: dto.ConfigEdit, db: Db, account: Account):
    await require(db, account, "system:config:update")
    await changes.update_row(db, m.config, int(id), changes.values(body, partial=True))
    await changes.commit(db)
    return success()


@router.delete("/configs/{id}")
async def delete_config(id: dto.Id, db: Db, account: Account):
    await require(db, account, "system:config:delete")
    await changes.delete_row(db, m.config, int(id))
    await changes.commit(db)
    return success()


@router.delete("/oper-logs")
async def clear_logs(request: Request, db: Db, account: Account):
    await require(db, account, "system:oper-log:clear")
    await db.execute(text("LOCK TABLE sys_oper_log IN SHARE ROW EXCLUSIVE MODE"))
    await db.execute(m.oper_log.delete())
    await write_log(db, request, 200)
    await db.commit()
    request.state.audit_written = True
    return success()

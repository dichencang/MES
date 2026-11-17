from fastapi import APIRouter
from sqlalchemy import select

from app.dto.auth import ChangePassword
from app.models import system as m
from app.routers.auth import Account, Db
from app.services.audit import AuditRoute
from app.services.auth import change_password
from app.services.permissions import granted_permissions, navigation_tree
from app.utils.responses import ApiError, success

router = APIRouter(tags=["系统管理"], route_class=AuditRoute)
PUBLIC_CONFIG_KEYS = frozenset({"sys.app.name"})


@router.put("/users/me/password")
async def update_my_password(body: ChangePassword, db: Db, account: Account):
    await change_password(db, account["id"], body)
    await db.commit()
    return success()


@router.get("/permissions/my")
async def my_permissions(db: Db, account: Account):
    rows = await granted_permissions(db, account["id"])
    return success({
        "tree": navigation_tree(rows),
        "permissionCodes": [row["permission_code"] for row in rows],
    })


@router.get("/configs/key/{key}")
async def read_config(key: str, db: Db, account: Account):
    if key in PUBLIC_CONFIG_KEYS:
        value = await db.scalar(select(m.config.c.config_value).where(m.config.c.config_key == key))
        if value is not None:
            return success({"configKey": key, "configValue": value})
    raise ApiError(404, 1002, "系统参数不存在")


@router.get("/dict-data/{dictCode}")
async def read_dictionary(dictCode: str, db: Db, account: Account):
    rows = (await db.execute(select(m.dict_data.c.dict_label, m.dict_data.c.dict_value)
        .join(m.dict_type)
        .where(m.dict_type.c.dict_code == dictCode, m.dict_type.c.status == "0",
               m.dict_data.c.status == "0")
        .order_by(m.dict_data.c.order_num, m.dict_data.c.id))).all()
    return success([{"dictLabel": label, "dictValue": value} for label, value in rows])

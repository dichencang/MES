from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import database_session
from app.dto.auth import Login, Refresh
from app.models import system as m
from app.services import auth
from app.utils.responses import ApiError, success

router = APIRouter(prefix="/auth", tags=["认证"])
Db = Annotated[AsyncSession, Depends(database_session)]
bearer = HTTPBearer(auto_error=False)


async def current_account(
    db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    if credentials is None:
        raise ApiError(401, 2001, "请先登录")
    return await auth.account_for_token(db, credentials.credentials)


Account = Annotated[dict, Depends(current_account)]


@router.post("/login")
async def login(body: Login, db: Db):
    async with db.begin():
        return success(await auth.login(db, body))


@router.post("/refresh")
async def refresh(body: Refresh, db: Db):
    async with db.begin():
        return success(await auth.refresh(db, body.refreshToken))


@router.post("/logout")
async def logout(body: Refresh, db: Db):
    async with db.begin():
        await auth.logout(db, body.refreshToken)
    return success()


@router.get("/me")
async def me(db: Db, account: Account):
    rows = await auth.roles_for_user(db, account["id"])
    roles = [
        {"id": str(row["id"]), "roleCode": row["role_code"], "roleName": row["role_name"]}
        for row in rows
    ]
    dept_name = await db.scalar(select(m.dept.c.dept_name).where(m.dept.c.id == account["dept_id"]))
    return success({
        "id": str(account["id"]), "username": account["username"],
        "realName": account["real_name"], "deptId": str(account["dept_id"]),
        "deptName": dept_name, "roles": roles,
        "roleCodes": [role["roleCode"] for role in roles],
        "isSuper": any(row["is_super"] == "1" for row in rows),
    })

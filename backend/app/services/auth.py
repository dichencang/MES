import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import func, or_, select

from app.config.settings import settings
from app.models import system as m
from app.utils.passwords import hash_password, verify_password
from app.utils.responses import ApiError

ACCESS_SECONDS = 1800
REFRESH_DAYS = 7


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def secret():
    value = settings().jwt_secret.get_secret_value()
    if len(value.encode()) < 32:
        raise RuntimeError("MES_JWT_SECRET must be at least 32 bytes")
    return value


async def issue(db, user_id, now):
    refresh = secrets.token_urlsafe(48)
    session_id = await db.scalar(m.user_session.insert().values(
        user_id=user_id, refresh_token_hash=digest(refresh),
        expires_at=now + timedelta(days=REFRESH_DAYS),
    ).returning(m.user_session.c.id))
    access = jwt.encode({
        "sub": str(user_id), "session_id": session_id,
        "iat": now, "exp": now + timedelta(seconds=ACCESS_SECONDS),
    }, secret(), algorithm="HS256")
    return {"accessToken": access, "refreshToken": refresh, "expiresIn": ACCESS_SECONDS}


async def login(db, body):
    account = (await db.execute(select(m.user).where(
        m.user.c.username == body.username, m.user.c.status == "0", m.user.c.del_flag == "0",
    ).with_for_update())).mappings().one_or_none()
    if account is None or not await verify_password(body.password, account["password_hash"]):
        raise ApiError(401, 2004, "账号或密码错误")
    now = datetime.now(UTC)
    await db.execute(m.user.update().where(m.user.c.id == account["id"]).values(last_login_time=now))
    return await issue(db, account["id"], now)


async def refresh(db, token):
    now = datetime.now(UTC)
    token_hash = digest(token)
    user_id = await db.scalar(select(m.user_session.c.user_id).where(
        m.user_session.c.refresh_token_hash == token_hash,
    ))
    account_id = await db.scalar(select(m.user.c.id).where(
        m.user.c.id == user_id, m.user.c.status == "0", m.user.c.del_flag == "0",
    ).with_for_update())
    if account_id is None:
        raise ApiError(401, 2003, "刷新令牌无效或已过期")
    consumed = await db.scalar(m.user_session.update().where(
        m.user_session.c.refresh_token_hash == token_hash,
        m.user_session.c.revoked_at.is_(None), m.user_session.c.expires_at > now,
    ).values(revoked_at=now, last_used_at=now, rotated=True).returning(m.user_session.c.id))
    if consumed is None:
        raise ApiError(401, 2003, "刷新令牌无效或已过期")
    return await issue(db, account_id, now)


async def logout(db, token):
    await db.execute(m.user_session.update().where(
        m.user_session.c.refresh_token_hash == digest(token), m.user_session.c.revoked_at.is_(None),
    ).values(revoked_at=datetime.now(UTC)))


async def account_for_token(db, token):
    try:
        claims = jwt.decode(token, secret(), algorithms=["HS256"], options={
            "require": ["exp", "sub", "session_id"], "verify_exp": False,
        })
    except jwt.InvalidTokenError as error:
        raise ApiError(401, 2001, "访问令牌无效或已过期") from error
    session = m.user_session
    now = datetime.now(UTC)
    account = (await db.execute(select(m.user, session.c.revoked_at, session.c.rotated).join(
        session, session.c.user_id == m.user.c.id,
    ).where(
        m.user.c.id == int(claims["sub"]), session.c.id == claims["session_id"],
        session.c.expires_at > now,
        m.user.c.status == "0", m.user.c.del_flag == "0",
    ))).mappings().one_or_none()
    if account is None or (account["revoked_at"] is not None and not account["rotated"]):
        raise ApiError(401, 2002, "会话已失效")
    if account["rotated"] or claims["exp"] <= now.timestamp():
        raise ApiError(401, 2001, "访问令牌无效或已过期")
    return account


async def roles_for_user(db, user_id):
    return (await db.execute(select(m.role).join(m.user_role).where(
        m.user_role.c.user_id == user_id,
    ).order_by(m.role.c.id))).mappings().all()


async def change_password(db, user_id, body):
    encoded = await db.scalar(select(m.user.c.password_hash).where(
        m.user.c.id == user_id, m.user.c.status == "0", m.user.c.del_flag == "0",
    ).with_for_update())
    if encoded is None:
        raise ApiError(401, 2002, "会话已失效")
    if not await verify_password(body.oldPassword, encoded):
        raise ApiError(400, 1001, "原密码错误")
    await db.execute(m.user.update().where(m.user.c.id == user_id).values(
        password_hash=await hash_password(body.newPassword), update_by=user_id,
        update_time=datetime.now(UTC),
    ))
    await revoke_user_sessions(db, user_id)


async def revoke_user_sessions(db, user_id):
    session = m.user_session
    await db.execute(session.update().where(
        session.c.user_id == user_id,
        or_(session.c.revoked_at.is_(None), session.c.rotated),
    ).values(revoked_at=func.coalesce(session.c.revoked_at, datetime.now(UTC)), rotated=False))

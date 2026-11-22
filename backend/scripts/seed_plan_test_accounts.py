"""Provision isolated non-admin plan acceptance accounts in a local MES database."""

from pathlib import Path
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config.database import engine
from app.models import system as m
from app.utils.event_loop import run
from app.utils.passwords import hash_password

ACCOUNTS = (
    ("plan_qa_reader", "计划验收-只读", "plan_qa_read", "只读计划管理"),
    ("plan_qa_writer", "计划验收-读写", "plan_qa_write", "计划管理"),
    ("plan_qa_denied", "计划验收-无权限", "plan_qa_none", "无计划权限"),
)
CREDENTIALS = Path(__file__).resolve().parents[1] / "docs" / "计划管理-本地验收账号.md"


async def provision():
    if engine.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("验收账号只允许写入本地数据库")
    credentials = []
    async with engine.begin() as db:
        dept_id = await db.scalar(select(m.user.c.dept_id).where(m.user.c.username == "admin"))
        permissions = (await db.execute(select(
            m.permission.c.id, m.permission.c.permission_code,
        ).where(m.permission.c.permission_code.like("plan:%"), m.permission.c.status == "0"))).all()
        if dept_id is None or len(permissions) < 10:
            raise SystemExit("请先初始化数据库和计划管理权限")
        for username, name, role_code, role_name in ACCOUNTS:
            role_id = await db.scalar(insert(m.role).values(
                role_code=role_code, role_name=role_name, data_scope="ALL",
            ).on_conflict_do_nothing(index_elements=[m.role.c.role_code]).returning(m.role.c.id))
            if role_id is None:
                raise SystemExit(f"验收角色 {role_code} 已存在，保留已有授权")
            password = token_urlsafe(18)
            user_id = await db.scalar(insert(m.user).values(
                username=username, real_name=name, dept_id=dept_id, password_hash=await hash_password(password),
            ).on_conflict_do_nothing(index_elements=[m.user.c.username]).returning(m.user.c.id))
            if user_id is None:
                raise SystemExit(f"验收账号 {username} 已存在，保留已有账号和密码")
            await db.execute(m.user_role.insert().values(user_id=user_id, role_id=role_id))
            for id, code in permissions:
                if role_code == "plan_qa_write" or (role_code == "plan_qa_read" and code.endswith(":list")):
                    await db.execute(insert(m.role_permission).values(
                        role_id=role_id, permission_id=id,
                    ).on_conflict_do_nothing())
            credentials.append(f"| {username} | {password} | {role_name} |")
        CREDENTIALS.parent.mkdir(exist_ok=True)
        with CREDENTIALS.open("x", encoding="utf-8") as file:
            file.write("# 计划管理本地验收账号\n\n| 账号 | 密码 | 权限 |\n| --- | --- | --- |\n")
            file.write("\n".join(credentials) + "\n")
    await engine.dispose()
    print("Created 3 local acceptance accounts. Passwords are in the ignored backend/docs credential file.")


if __name__ == "__main__":
    run(provision())

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.config.settings import settings
from app.models import system as m
from app.models.basic_seed import seed_statements
from app.models.plan_seed import permission_statements, seed_sample
from app.models.seed_data import BUSINESS_MODULES, PERMISSIONS
from app.models import workorder_seed
from app.utils.passwords import hash_password

DICTIONARIES = {
    "sys_status": ("通用状态", [("正常", "0"), ("停用", "1")]),
    "sys_yes_no": ("是否", [("是", "1"), ("否", "0")]),
    "sys_data_scope": ("数据范围", [
        ("全部数据", "ALL"), ("自定义部门", "CUSTOM"), ("本部门", "DEPT"),
        ("本部门及以下", "DEPT_CHILD"), ("仅本人", "SELF"),
    ]),
    "sys_perm_type": ("权限类型", [("目录", "DIR"), ("菜单", "MENU"), ("按钮", "BUTTON")]),
    "sys_config_type": ("参数类型", [("内置", "0"), ("自定义", "1")]),
}


async def seed_business_permissions(connection):
    permission = m.permission

    async def ensure_node(code, **fields):
        await connection.execute(insert(permission).values(
            permission_code=code, **fields,
        ).on_conflict_do_nothing(index_elements=[permission.c.permission_code]))

    await ensure_node(
        "home:workbench:list", perm_name="工作台", perm_type="MENU",
        path="/home", component="home/index", icon="Odometer",
    )
    for order, (module, directory, icon) in enumerate(BUSINESS_MODULES, 1):
        path = f"/{module}"
        await ensure_node(
            module, perm_name=directory, perm_type="DIR",
            path=path, icon=icon, order_num=order,
        )
    for statement in (*seed_statements(), *permission_statements(), *workorder_seed.permission_statements()):
        await connection.execute(statement)


async def seed_system(connection):
    if await connection.scalar(select(m.user.c.id).where(m.user.c.username == "admin")):
        await seed_business_permissions(connection)
        await seed_sample(connection)
        await workorder_seed.seed_sample(connection)
        return
    await connection.execute(m.dept.insert().values(id=1, dept_name="总部", order_num=1))
    await connection.execute(m.role.insert().values(
        id=1, role_code="super_admin", role_name="超级管理员", data_scope="ALL", is_super="1",
    ))
    password = settings().seed_admin_password.get_secret_value()
    password_hash = await hash_password(password)
    await connection.execute(m.user.insert().values(
        id=1, username="admin", real_name="系统管理员", dept_id=1, is_builtin="1",
        password_hash=password_hash,
    ))
    await connection.execute(m.user_role.insert().values(user_id=1, role_id=1))
    fields = ("id", "parent_id", "perm_name", "perm_type", "permission_code", "path",
              "component", "icon", "order_num")
    await connection.execute(m.permission.insert(), [dict(zip(fields, row)) for row in PERMISSIONS])
    for code, (name, items) in DICTIONARIES.items():
        await connection.execute(m.dict_type.insert().values(dict_code=code, dict_name=name))
        await connection.execute(m.dict_data.insert(), [
            dict(dict_code=code, dict_label=label, dict_value=value, order_num=index)
            for index, (label, value) in enumerate(items, 1)
        ])
    await connection.execute(m.config.insert(), [
        dict(config_key=key, config_name=name, config_value=value, config_type="0")
        for key, name, value in [
            ("sys.app.name", "系统名称", "MES 生产制造执行系统"),
            ("sys.token.accessMinutes", "访问令牌有效分钟", "30"),
            ("sys.token.refreshDays", "刷新会话有效天数", "7"),
        ]
    ])
    for table in (m.dept, m.role, m.user, m.permission):
        await connection.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), MAX(id)) FROM {table.name}"
        ))
    await seed_business_permissions(connection)
    await seed_sample(connection)
    await workorder_seed.seed_sample(connection)

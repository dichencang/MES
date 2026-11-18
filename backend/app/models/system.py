from sqlalchemy import (
    BigInteger, Boolean, CHAR, CheckConstraint, Column, DateTime, ForeignKey, Index,
    Integer, MetaData, String, Table, Text, UniqueConstraint, func,
)

metadata = MetaData()


def entity(name, *columns):
    return Table(name, metadata, Column("id", BigInteger, primary_key=True), *columns)


def timestamp(name, *, nullable=False, default=True):
    return Column(
        name, DateTime(timezone=True), nullable=nullable,
        server_default=func.now() if default else None,
    )


def flag(name, default="0"):
    return Column(name, CHAR(1), CheckConstraint(f"{name} IN ('0','1')"),
                  nullable=False, server_default=default)


def parent():
    return Column("parent_id", BigInteger, nullable=False, server_default="0")


dept = entity(
    "sys_dept", parent(), Column("dept_name", String(64), nullable=False),
    Column("order_num", Integer, nullable=False, server_default="0"),
    Column("leader", String(64)), Column("phone", String(20)), flag("status"),
    timestamp("create_time"), timestamp("update_time"),
)
user = entity(
    "sys_user", Column("username", String(64), nullable=False, unique=True),
    Column("password_hash", String(128), nullable=False),
    Column("real_name", String(64), nullable=False),
    Column("dept_id", ForeignKey(dept.c.id), nullable=False, index=True),
    Column("phone", String(20)), Column("email", String(128)), flag("status"),
    flag("del_flag"), flag("is_builtin"),
    timestamp("last_login_time", nullable=True, default=False),
    Column("create_by", BigInteger), Column("update_by", BigInteger),
    timestamp("create_time"), timestamp("update_time"),
)
role = entity(
    "sys_role", Column("role_name", String(64), nullable=False),
    Column("role_code", String(64), nullable=False, unique=True),
    Column("data_scope", String(20), nullable=False),
    CheckConstraint("data_scope IN ('ALL','CUSTOM','DEPT','DEPT_CHILD','SELF')"),
    flag("is_super"), Column("remark", String(256)),
    timestamp("create_time"), timestamp("update_time"),
)
permission = entity(
    "sys_permission", parent(), Column("perm_name", String(64), nullable=False),
    Column("perm_type", String(16), nullable=False),
    CheckConstraint("perm_type IN ('DIR','MENU','BUTTON')"),
    Column("permission_code", String(128), nullable=False, unique=True),
    Column("path", String(128)), Column("component", String(128)),
    Column("icon", String(64)), Column("order_num", Integer, nullable=False, server_default="0"),
    flag("visible"), flag("status"),
)


def association(name, left_name, left, right_name, right):
    return Table(
        name, metadata,
        Column(left_name, ForeignKey(left.c.id), primary_key=True),
        Column(right_name, ForeignKey(right.c.id), primary_key=True, index=True),
    )


user_role = association("sys_user_role", "user_id", user, "role_id", role)
role_permission = association(
    "sys_role_permission", "role_id", role, "permission_id", permission,
)
role_dept = association("sys_role_dept", "role_id", role, "dept_id", dept)

dict_type = entity(
    "sys_dict_type", Column("dict_name", String(64), nullable=False),
    Column("dict_code", String(64), nullable=False, unique=True), flag("status"),
    Column("remark", String(256)),
)
dict_data = entity(
    "sys_dict_data", Column("dict_code", ForeignKey(dict_type.c.dict_code), nullable=False),
    Column("dict_label", String(64), nullable=False),
    Column("dict_value", String(64), nullable=False),
    Column("order_num", Integer, nullable=False, server_default="0"), flag("status"),
    UniqueConstraint("dict_code", "dict_value"),
)
config = entity(
    "sys_config", Column("config_name", String(64), nullable=False),
    Column("config_key", String(128), nullable=False, unique=True),
    Column("config_value", String(512), nullable=False), flag("config_type", "1"),
    Column("remark", String(256)), timestamp("create_time"), timestamp("update_time"),
)
oper_log = entity(
    "sys_oper_log", Column("operator_id", BigInteger),
    Column("operator_name", String(64)), Column("module", String(64), nullable=False),
    Column("operation", String(128), nullable=False), Column("method", String(256), nullable=False),
    Column("request_url", String(256), nullable=False), Column("request_param", Text),
    Column("ip", String(64)), flag("status"), Column("error_msg", String(512)),
    Column("cost_time", BigInteger, nullable=False), timestamp("oper_time"),
)
Index("ix_sys_oper_log_oper_time_id", oper_log.c.oper_time, oper_log.c.id)

user_session = entity(
    "sys_user_session", Column("user_id", ForeignKey(user.c.id), nullable=False, index=True),
    Column("refresh_token_hash", String(64), nullable=False, unique=True),
    timestamp("expires_at", default=False),
    timestamp("revoked_at", nullable=True, default=False),
    Column("rotated", Boolean, nullable=False, server_default="false"),
    timestamp("created_at"),
    timestamp("last_used_at", nullable=True, default=False),
)

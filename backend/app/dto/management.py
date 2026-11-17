from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.dto.auth import Password


def checked_id(value: str) -> str:
    if int(value) > 9223372036854775807:
        raise ValueError("ID 超出范围")
    return value


Id = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,18}$"), AfterValidator(checked_id)]
ParentId = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$"), AfterValidator(checked_id)]
Flag = Literal["0", "1"]
Name = Annotated[str, Field(min_length=1, max_length=64)]
Text64 = Annotated[str, Field(max_length=64)]
Text128 = Annotated[str, Field(max_length=128)]
Remark = Annotated[str, Field(max_length=256)]
ConfigValue = Annotated[str, Field(max_length=512)]
Phone = Annotated[str, Field(max_length=20)]
Scope = Literal["ALL", "CUSTOM", "DEPT", "DEPT_CHILD", "SELF"]
Order = Annotated[int, Field(ge=0, le=2147483647)]


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")


class UserEdit(Body):
    real_name: Name
    dept_id: Id
    phone: Phone | None = None
    email: Text128 | None = None


class UserCreate(UserEdit):
    username: Name
    password: Password
    role_ids: list[Id]
    status: Flag = "0"


class UserRoles(Body):
    role_ids: list[Id]


class Status(Body):
    status: Flag


class PasswordReset(Body):
    password: Password


class RoleEdit(Body):
    role_name: Name
    remark: Remark | None = None


class DataScope(Body):
    data_scope: Scope
    dept_ids: list[Id] = Field(default_factory=list)


class RoleCreate(RoleEdit, DataScope):
    role_code: Name


class RolePermissions(Body):
    permission_ids: list[Id]


class Department(Body):
    parent_id: ParentId = "0"
    dept_name: Name
    order_num: Order = 0
    leader: Text64 | None = None
    phone: Phone | None = None
    status: Flag = "0"


class PermissionEdit(Body):
    parent_id: ParentId = "0"
    perm_name: Name
    perm_type: Literal["DIR", "MENU", "BUTTON"]
    path: Text128 | None = None
    component: Text128 | None = None
    icon: Text64 | None = None
    order_num: Order = 0
    visible: Flag = "0"
    status: Flag = "0"


class PermissionCreate(PermissionEdit):
    permission_code: Annotated[str, Field(min_length=1, max_length=128)]


class DictTypeEdit(Body):
    dict_name: Name
    status: Flag = "0"
    remark: Remark | None = None


class DictTypeCreate(DictTypeEdit):
    dict_code: Name


class DictItemEdit(Body):
    dict_label: Name
    dict_value: Name
    order_num: Order = 0
    status: Flag = "0"


class DictItemCreate(DictItemEdit):
    dict_code: Name


class ConfigEdit(Body):
    config_value: ConfigValue
    config_name: Name = Field(default="")
    remark: Remark | None = None


class ConfigCreate(Body):
    config_name: Name
    config_key: Annotated[str, Field(min_length=1, max_length=128)]
    config_value: ConfigValue
    remark: Remark | None = None

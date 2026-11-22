import json
from time import perf_counter

from fastapi.routing import APIRoute
from sqlalchemy.exc import IntegrityError

from app.config.database import SessionLocal
from app.models import system as m
from app.utils.responses import ApiError

MODULE_NAMES = {
    "users": "用户管理", "roles": "角色管理", "permissions": "权限管理",
    "depts": "组织架构", "dict-types": "数据字典", "dict-data": "数据字典",
    "configs": "系统参数", "oper-logs": "操作日志", "auth": "认证",
    "materials": "物料档案", "processes": "工序档案", "boms": "产品 BOM", "routings": "工艺路线",
}
SECRET_KEYS = {
    "password", "oldpassword", "newpassword", "refreshtoken", "accesstoken", "authorization",
    "captchaid", "captchacode", "drafttoken",
}


def redact(value):
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        key_name = key.lower().replace("_", "")
        if key_name in SECRET_KEYS:
            item = "***"
        elif key_name == "phone" and isinstance(item, str):
            item = item[:3] + "***" + item[-3:] if len(item) > 6 else "***"
        elif key_name == "email" and isinstance(item, str):
            local, separator, domain = item.partition("@")
            item = local[:1] + "***" + separator + domain if separator else "***"
        else:
            item = redact(item)
        result[key] = item
    return result


async def write_log(db, request, status, error=None):
    account = getattr(request.state, "audit_account", None)
    params = getattr(request.state, "audit_params", None)
    route = request.scope["route"]
    path = request.url.path
    resource = path.split("/")[1]
    if resource == "plan":
        module = "销售订单" if path.startswith("/plan/sales-orders") else "生产计划"
    else:
        module = MODULE_NAMES[resource]
    action = {
        "/auth/login": "登录", "/auth/logout": "登出",
        "/users/me/password": "修改本人密码", "/oper-logs": "清空操作日志",
    }.get(path)
    if resource == "plan":
        action = {"cancel": "取消", "transfer": "转工单"}.get(path.rsplit("/", 1)[-1], action)
    if action is None:
        action = {"POST": "新增", "PUT": "修改", "DELETE": "删除"}[request.method] + module
    await db.execute(m.oper_log.insert().values(
        operator_id=account["id"] if account else None,
        operator_name=account["username"] if account else None,
        module=module, operation=action,
        method=f"{route.endpoint.__module__}.{route.name}",
        request_url=path[:256],
        request_param=json.dumps(params, ensure_ascii=False) if params is not None else None,
        ip=request.client.host if request.client else None,
        status="0" if status < 400 else "1", error_msg=error,
        cost_time=int((perf_counter() - request.state.audit_start) * 1000),
    ))


class AuditRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        if self.path == "/auth/refresh" or self.methods == {"GET"}:
            return handler

        async def audited(request):
            from app.services.changes import integrity_error

            request.state.audit_start = perf_counter()
            try:
                body = await request.json()
                if isinstance(body, dict):
                    request.state.audit_params = redact(body)
            except (ValueError, UnicodeError):
                pass
            try:
                response = await handler(request)
            except IntegrityError as error:
                api_error = integrity_error(error)
                await audit(request, api_error.status, api_error.message)
                raise api_error from error
            except ApiError as error:
                await audit(request, error.status, error.message)
                raise
            except Exception as error:
                from fastapi.exceptions import RequestValidationError

                if isinstance(error, RequestValidationError):
                    await audit(request, 400, "参数校验失败")
                else:
                    await audit(request, 500, "服务端错误")
                raise
            if not getattr(request.state, "audit_written", False):
                await audit(request, response.status_code)
            return response

        return audited


async def audit(request, status, error=None):
    async with SessionLocal.begin() as db:
        await write_log(db, request, status, error)

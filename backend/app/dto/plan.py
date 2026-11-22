import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, StringConstraints

from app.dto.management import Body, Id

OrderStatus = Literal["CANCELLED", "COMPLETED", "IN_PRODUCTION", "SCHEDULED", "PENDING_SCHEDULING"]
PlanStatus = Literal["CANCELLED", "TRANSFERRED", "PENDING_TRANSFER"]
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("日期格式须为 YYYY-MM-DD")
    return date.fromisoformat(value)


def parse_utc(value):
    pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError("时间须为 UTC Z 格式")
    return datetime.fromisoformat(value)


def parse_quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,14}(\.[0-9]{1,4})?", value):
        raise ValueError("数量须为最多四位小数的十进制字符串")
    quantity = Decimal(value)
    if quantity <= 0:
        raise ValueError("数量必须大于零")
    return quantity


DateString = Annotated[date, BeforeValidator(parse_date, json_schema_input_type=str)]
UtcTimestamp = Annotated[datetime, BeforeValidator(parse_utc, json_schema_input_type=str)]
Quantity = Annotated[Decimal, BeforeValidator(parse_quantity, json_schema_input_type=str)]


class ItemInput(Body):
    id: Id | None = None
    line_no: Annotated[int, Field(strict=True, gt=0, le=2147483647)]
    product_id: Id
    order_qty: Quantity
    due_date: DateString


class SalesOrderInput(Body):
    customer_name: NonBlank
    order_date: DateString
    remark: str | None
    items: Annotated[list[ItemInput], Field(min_length=1)]


class PlanUpdate(Body):
    planned_qty: Quantity
    planned_start_at: UtcTimestamp
    planned_end_at: UtcTimestamp
    remark: str | None


class PlanCreate(PlanUpdate):
    order_item_id: Id
    remark: str | None = None


class Cancel(Body):
    cancel_reason: NonBlank

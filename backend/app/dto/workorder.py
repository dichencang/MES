from typing import Annotated, Literal

from pydantic import StringConstraints

from app.dto.management import Body, Id
from app.dto.plan import PlanUpdate

Status = Literal["PENDING_RELEASE", "RELEASED", "IN_PRODUCTION", "COMPLETED", "CLOSED", "CANCELLED"]


class Create(PlanUpdate):
    product_id: Id
    remark: str | None = None


class Cancel(Body):
    cancel_reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class Assign(Body):
    assignee_ids: list[Id]

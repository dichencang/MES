from typing import Annotated, Literal

from pydantic import Field

from app.dto.management import Body, Id

Code = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,50}$")]
Name = Annotated[str, Field(min_length=1, max_length=100)]
ShortText = Annotated[str, Field(max_length=100)]
Note = Annotated[str, Field(max_length=200)]
DictCode = Annotated[str, Field(min_length=1, max_length=64)]
Quantity = Annotated[str, Field(pattern=r"^-?[0-9]{1,14}(\.[0-9]{1,4})?$")]
Token = Annotated[str, Field(min_length=1, max_length=200)]
Seq = Annotated[int, Field(strict=True, ge=-2147483648, le=2147483647)]
ConfigStatus = Literal["all", "configured", "draft-only", "unconfigured"]


class MaterialEdit(Body):
    name: Name
    category_code: DictCode
    spec: ShortText | None = None
    is_product: Annotated[bool, Field(strict=True)]
    remark: Note | None = None


class MaterialCreate(MaterialEdit):
    code: Code
    unit_code: DictCode


class ProcessEdit(Body):
    name: Name
    description: Note | None = None


class ProcessCreate(ProcessEdit):
    code: Code


class VersionCreate(Body):
    product_id: Id
    source_version_id: Id | None = None


class BomItem(Body):
    item_id: Id | None = None
    material_id: Id
    qty: Quantity


class RoutingStep(Body):
    step_id: Id | None = None
    process_id: Id
    seq: Seq
    remark: Note | None = None


class BomSave(Body):
    draft_token: Token
    base_qty: Quantity
    items: list[BomItem]


class RoutingSave(Body):
    draft_token: Token
    steps: list[RoutingStep]


class Publish(Body):
    draft_token: Token
    expected_active_version_id: Id | None

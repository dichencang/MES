from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, or_, select, text

from app.models import basic as m
from app.models import system as sys
from app.services.changes import commit
from app.services.management import existing, filters, pagination, rows, serialize
from app.utils.responses import ApiError


@dataclass(frozen=True)
class Definition:
    table: object
    detail: object
    owner: str
    reference: str
    collection: str
    scope: str
    ordering: str


BOM = Definition(m.bom, m.bom_item, "bom_id", "material_id", "items", "item", "sort_no")
ROUTING = Definition(m.routing, m.routing_step, "routing_id", "process_id", "steps", "step", "seq")
PRODUCT_FIELDS = "product_id product_code product_name"
MATERIAL_FIELDS = "id code name category_code category_label spec unit_code unit_name status is_product remark"
PROCESS_FIELDS = "id code name description status"


def invalid(field, message):
    return ApiError(400, 1001, "参数校验失败", {"errors": [{"field": field, "message": message}]})


async def module_lock(db):
    await db.execute(text("SELECT pg_advisory_xact_lock(684312, 1)"))


async def locked(db, table, id, *, no_key=False):
    row = (await db.execute(select(table).where(table.c.id == id)
                            .with_for_update(key_share=no_key))).mappings().one_or_none()
    if row is None:
        raise ApiError(404, 1002, "记录不存在")
    return row


def keyword_filter(statement, table, keyword):
    if keyword:
        statement = statement.where(or_(
            table.c.code.icontains(keyword, autoescape=True),
            table.c.name.icontains(keyword, autoescape=True),
        ))
    return statement


def material_query():
    category = sys.dict_data.alias("category")
    unit = sys.dict_data.alias("unit")
    c = m.material.c
    return select(m.material, category.c.dict_label.label("category_label"), unit.c.dict_label.label("unit_name")).join(
        category, (category.c.dict_code == c.category_dict_code) & (category.c.dict_value == c.category_code)
    ).join(unit, (unit.c.dict_code == c.unit_dict_code) & (unit.c.dict_value == c.unit_code))


async def archives(db, table, keyword, status, page, size, *, category=None, product=None, options=False):
    material = table is m.material
    statement = material_query() if material else select(table)
    exact = [(table.c.status, status)]
    if material:
        exact.extend(((table.c.category_code, category), (table.c.is_product, product)))
    statement = filters(keyword_filter(statement, table, keyword), exact=exact)
    total, records = await pagination(db, statement.order_by(table.c.code, table.c.id), page, size)
    fields = MATERIAL_FIELDS if material else PROCESS_FIELDS
    if options:
        fields = ("id code name spec category_code category_label unit_name status is_product"
                  if material else "id code name status")
    return {"total": total, "list": [serialize(row, fields) for row in records]}


async def check_dictionary(db, kind, value, field):
    item, group = sys.dict_data, sys.dict_type
    enabled = await db.scalar(select(item.c.id).join(group).where(
        item.c.dict_code == kind, item.c.dict_value == value, item.c.status == "0", group.c.status == "0",
    ))
    if enabled is None:
        raise invalid(field, "请选择启用的字典项")


async def check_references(db, table, id, *, parent_only=False):
    references = []
    for definition in (BOM, ROUTING):
        version, detail = definition.table, definition.detail
        if table is m.process and definition is BOM:
            continue
        condition = version.c.product_id == id
        if table is m.process:
            condition = select(detail.c.id).where(
                detail.c[definition.owner] == version.c.id, detail.c.process_id == id,
            ).exists()
        elif definition is BOM and not parent_only:
            condition = or_(condition, select(detail.c.id).where(
                detail.c.bom_id == version.c.id, detail.c.material_id == id,
            ).exists())
        references.extend({
            "configType": "BOM" if definition is BOM else "ROUTING",
            "productCode": record.code, "productName": record.name,
            "version": f"V{record.version}", "versionStatus": "生效",
        } for record in await db.execute(
            select(m.material.c.code, m.material.c.name, version.c.version)
            .join(version, version.c.product_id == m.material.c.id)
            .where(condition, version.c.status == "1").order_by(m.material.c.code, version.c.id)
        ))
    if references:
        raise ApiError(409, 4003, "档案正被生效配置引用", {"references": references})


async def write_archive(db, table, body, id=None):
    values = body.model_dump()
    if table is m.material:
        if id is not None:
            await module_lock(db)
            previous = await locked(db, table, id, no_key=True)
            if previous["is_product"] and not values["is_product"]:
                await check_references(db, table, id, parent_only=True)
        if id is None or previous["category_code"] != values["category_code"]:
            await check_dictionary(db, "material_category", values["category_code"], "categoryCode")
        if id is None:
            await check_dictionary(db, "material_unit", values["unit_code"], "unitCode")
    elif id is not None:
        await locked(db, table, id, no_key=True)
    statement = table.insert() if id is None else table.update().where(table.c.id == id)
    result_id = await db.scalar(statement.values(**values).returning(table.c.id))
    statement = material_query() if table is m.material else select(table)
    result = (await db.execute(statement.where(table.c.id == result_id))).mappings().one()
    await commit(db)
    return serialize(result, MATERIAL_FIELDS if table is m.material else PROCESS_FIELDS)


async def set_status(db, table, id, status):
    await module_lock(db)
    record = await locked(db, table, id, no_key=True)
    if status == "1" and record["status"] == "0":
        await check_references(db, table, id)
    await db.execute(table.update().where(table.c.id == id).values(status=status))
    await commit(db)


def version_label(record, fields):
    return dict(serialize(record, fields), versionLabel=f"V{record['version']}")


def summary(record):
    return version_label(record, "id version status published_at create_time")


def active_summary(record):
    if record is None:
        return None
    return version_label(record, "id version published_at publisher_name")


def version_query(table):
    publisher = sys.user.alias("publisher")
    return select(table, publisher.c.real_name.label("publisher_name")).outerjoin(
        publisher, publisher.c.id == table.c.publisher_id
    )


def product_query():
    statement = material_query()
    return statement.with_only_columns(
        m.material.c.id.label("product_id"), m.material.c.code.label("product_code"),
        m.material.c.name.label("product_name"), m.material.c.spec,
        m.material.c.status.label("product_status"),
        statement.selected_columns.unit_name,
    )


async def product_list(db, definition, keyword, config_status, page, size):
    table, material = definition.table, m.material
    active = select(table.c.id).where(table.c.product_id == material.c.id, table.c.status == "1").exists()
    draft = select(table.c.id).where(table.c.product_id == material.c.id, table.c.status == "0").exists()
    statement = keyword_filter(product_query().where(material.c.is_product), material, keyword)
    if config_status == "configured":
        statement = statement.where(active)
    elif config_status == "draft-only":
        statement = statement.where(~active, draft)
    elif config_status == "unconfigured":
        statement = statement.where(~active, ~draft)
    total, products = await pagination(db, statement.order_by(material.c.code, material.c.id), page, size)
    grouped = defaultdict(list)
    if products:
        for record in await rows(db, version_query(table).where(
            table.c.product_id.in_([product["product_id"] for product in products])
        ).order_by(table.c.version.desc())):
            grouped[record["product_id"]].append(record)
    result = []
    for product in products:
        versions = grouped[product["product_id"]]
        actual = next((record for record in versions if record["status"] == "1"), None)
        latest = next((record for record in versions if record["status"] == "0"), None)
        updated = max((record["update_time"] for record in versions), default=None)
        result.append(dict(
            serialize(product, f"{PRODUCT_FIELDS} spec product_status unit_name"),
            activeVersion=active_summary(actual), latestDraft=summary(latest) if latest else None,
            versionCount=len(versions), **serialize({"update_time": updated}, "update_time"),
        ))
    return {"total": total, "list": result}


async def version_details(db, definition, id):
    table, detail = definition.table, definition.detail
    record = await existing(db, table, id)
    product = await existing(db, m.material, record["product_id"])
    editor = await existing(db, sys.user, record["last_editor_id"])
    versions = await rows(db, version_query(table).where(table.c.product_id == product["id"])
                          .order_by(table.c.version.desc()))
    actual = next((version for version in versions if version["status"] == "1"), None)
    result = version_label(record, "id product_id version status create_time update_time")
    detail_query = select(detail, detail.c.id.label(f"{definition.scope}_id"))
    if definition is BOM:
        material = m.material
        unit = sys.dict_data
        detail_query = detail_query.add_columns(
            material.c.code.label("material_code"), material.c.name.label("material_name"),
            material.c.status.label("material_status"), unit.c.dict_label.label("unit_name"),
        ).join(material, material.c.id == detail.c.material_id).join(
            unit, (unit.c.dict_code == material.c.unit_dict_code) & (unit.c.dict_value == material.c.unit_code),
        )
        fields = "item_id material_id material_code material_name material_status unit_name sort_no"
        result["baseQty"] = format(record["base_qty"], ".4f")
    else:
        process = m.process
        detail_query = detail_query.add_columns(
            process.c.code.label("process_code"), process.c.name.label("process_name"),
            process.c.status.label("process_status"),
        ).join(process, process.c.id == detail.c.process_id)
        fields = "step_id seq process_id process_code process_name process_status remark"
    lines = await rows(db, detail_query.where(detail.c[definition.owner] == id)
                       .order_by(detail.c[definition.ordering], detail.c.id))
    result.update(
        productCode=product["code"], productName=product["name"], lastEditorName=editor["real_name"],
        draftToken=str(record["draft_token"]) if record["draft_token"] else None,
        activeVersion=active_summary(actual), versions=[summary(version) for version in versions],
    )
    result[definition.collection] = [
        dict(serialize(line, fields), qty=format(line["qty"], ".4f"))
        if definition is BOM else serialize(line, fields) for line in lines
    ]
    return result


async def new_version(db, definition, body, actor):
    product_id = int(body.product_id)
    product = await locked(db, m.material, product_id, no_key=True)
    if product["status"] != "0" or not product["is_product"]:
        raise invalid("productId", "请选择启用且可生产的物料")
    table, detail = definition.table, definition.detail
    source = None
    if body.source_version_id:
        source = await locked(db, table, int(body.source_version_id))
        if source["product_id"] != product_id:
            raise invalid("sourceVersionId", "只能复制同一产品的版本")
    counter = "bom_max_version" if definition is BOM else "routing_max_version"
    maximum = await db.scalar(select(func.max(table.c.version)).where(table.c.product_id == product_id))
    version = max(product[counter], maximum or 0) + 1
    await db.execute(m.material.update().where(m.material.c.id == product_id).values({counter: version}))
    values = dict(product_id=product_id, version=version, draft_token=uuid4(), last_editor_id=actor)
    if source and definition is BOM:
        values["base_qty"] = source["base_qty"]
    id = await db.scalar(table.insert().values(**values).returning(table.c.id))
    if source:
        columns = [column for column in detail.c if column.name not in ("id", definition.owner)]
        source_lines = await rows(db, select(*columns).where(detail.c[definition.owner] == source["id"])
                                  .order_by(detail.c[definition.ordering], detail.c.id))
        if source_lines:
            await db.execute(detail.insert(), [dict(line, **{definition.owner: id}) for line in source_lines])
    result = await version_details(db, definition, id)
    await commit(db)
    return result


async def check_draft(db, record, token):
    if record["status"] != "0":
        raise ApiError(409, 4005, "仅草稿允许此操作")
    if str(record["draft_token"]) != token:
        editor = await existing(db, sys.user, record["last_editor_id"])
        raise ApiError(409, 4001, "草稿已被修改", dict(
            lastEditorName=editor["real_name"],
            **serialize({"last_updated_at": record["update_time"]}, "last_updated_at"),
        ))


async def save_version(db, definition, id, body, actor):
    table, detail = definition.table, definition.detail
    record = await locked(db, table, id)
    await check_draft(db, record, body.draft_token)
    drafts = getattr(body, definition.collection)
    line_key = f"{definition.scope}_id"
    id_field = "itemId" if definition is BOM else "stepId"
    reference_field = "materialId" if definition is BOM else "processId"
    reference_table = m.material if definition is BOM else m.process
    provided = [int(getattr(line, line_key)) for line in drafts if getattr(line, line_key) is not None]
    owners = dict((await db.execute(
        select(detail.c.id, detail.c[definition.owner]).where(detail.c.id.in_(provided))
    )).all()) if provided else {}
    referenced = {int(getattr(line, definition.reference)) for line in drafts}
    available = set(await db.scalars(
        select(reference_table.c.id).where(reference_table.c.id.in_(referenced))
    )) if referenced else set()
    seen, retained, inserts = set(), set(), []
    updates = []
    for index, line in enumerate(drafts):
        path = f"{definition.collection}[{index}]"
        payload = line.model_dump(exclude={line_key})
        reference = int(payload[definition.reference])
        if reference not in available:
            raise invalid(f"{path}.{reference_field}", "引用不存在")
        payload[definition.reference] = reference
        if definition is BOM:
            payload.update(qty=Decimal(payload["qty"]), sort_no=index + 1)
        line_id = getattr(line, line_key)
        if line_id is not None:
            line_id = int(line_id)
            if line_id in seen or (line_id in owners and owners[line_id] != id):
                raise invalid(f"{path}.{id_field}", "行 ID 重复或属于其他版本")
            seen.add(line_id)
        if line_id in owners:
            retained.add(line_id)
            updates.append((line_id, payload))
        else:
            inserts.append(dict(payload, **{definition.owner: id}))
    await db.execute(detail.delete().where(detail.c[definition.owner] == id, detail.c.id.not_in(retained)))
    for line_id, payload in updates:
        await db.execute(detail.update().where(detail.c.id == line_id).values(**payload))
    if inserts:
        await db.execute(detail.insert(), inserts)
    changes = dict(draft_token=uuid4(), last_editor_id=actor, update_time=datetime.now(UTC))
    if definition is BOM:
        changes["base_qty"] = Decimal(body.base_qty)
    await db.execute(table.update().where(table.c.id == id).values(**changes))
    result = await version_details(db, definition, id)
    await commit(db)
    return result


async def delete_version(db, definition, id, token):
    table = definition.table
    await check_draft(db, await locked(db, table, id), token)
    await db.execute(table.delete().where(table.c.id == id))
    await commit(db)


async def cycle_children(db, product_id, children):
    if not children:
        return set()
    # Traverse backwards from the candidate parent. Its existing outgoing edges will be replaced.
    table, detail = m.bom, m.bom_item
    ancestors = select(m.material.c.id.label("id")).where(m.material.c.id == product_id).cte(recursive=True)
    upstream = select(table.c.product_id.label("id")).join(detail, detail.c.bom_id == table.c.id).join(
        ancestors, ancestors.c.id == detail.c.material_id,
    ).where(table.c.status == "1", table.c.product_id != product_id)
    ancestors = ancestors.union(upstream)
    return set(await db.scalars(select(ancestors.c.id).where(ancestors.c.id.in_(children))))


async def validate_publish(db, definition, product, record):
    detail = definition.detail
    lines = await rows(db, select(detail).where(detail.c[definition.owner] == record["id"])
                       .order_by(detail.c[definition.ordering], detail.c.id))
    reasons = []

    def header(field, code, message):
        reasons.append(dict(scope="header", field=field, code=code, message=message))

    def line_error(line, index, code, message):
        reasons.append(dict(scope=definition.scope, lineNo=index, code=code, message=message,
                            **{f"{definition.scope}Id": str(line["id"])}))

    if product["status"] != "0" or not product["is_product"]:
        header("productId", "PRODUCT_NOT_ELIGIBLE", "产品已停用或已取消可生产标志")
    if not lines:
        header(definition.collection, "ITEM_EMPTY", "明细不能为空")
    references = {line[definition.reference] for line in lines}
    reference_table = m.material if definition is BOM else m.process
    statuses = dict((await db.execute(select(reference_table.c.id, reference_table.c.status)
                                     .where(reference_table.c.id.in_(references)))).all()) if references else {}
    if definition is BOM:
        base_qty = record["base_qty"]
        if base_qty <= 0 or base_qty != base_qty.to_integral_value():
            header("baseQty", "QTY_INVALID", "基准产量需为大于 0 的整数")
        cyclic = await cycle_children(db, product["id"], references)
    else:
        sequence_counts = Counter(line["seq"] for line in lines)
    for index, line in enumerate(lines, 1):
        reference_id = line[definition.reference]
        status = statuses.get(reference_id)
        if status is None:
            line_error(line, index, "REFERENCE_MISSING", "引用档案不存在")
        elif status != "0":
            code = "MATERIAL_DISABLED" if definition is BOM else "PROCESS_DISABLED"
            line_error(line, index, code, "引用档案已停用")
        if definition is BOM:
            if line["qty"] <= 0:
                line_error(line, index, "QTY_INVALID", "子件用量必须大于 0")
            if reference_id in cyclic:
                line_error(line, index, "BOM_CYCLE", "子件形成循环引用")
        else:
            seq = line["seq"]
            if not 1 <= seq <= 9999:
                line_error(line, index, "STEP_SEQ_INVALID", "步骤序号须为 1 至 9999 的整数")
            if sequence_counts[seq] > 1:
                line_error(line, index, "STEP_SEQ_DUPLICATE", "步骤序号重复")
    if reasons:
        raise ApiError(409, 4004, reasons[0]["message"], {"reasons": reasons})


async def publish_version(db, definition, id, body, actor):
    table = definition.table
    await module_lock(db)
    record = await existing(db, table, id)
    product = await locked(db, m.material, record["product_id"], no_key=True)
    record = await locked(db, table, id)
    await check_draft(db, record, body.draft_token)
    current = (await db.execute(version_query(table).where(
        table.c.product_id == product["id"], table.c.status == "1",
    ))).mappings().one_or_none()
    actual = active_summary(current)
    if (actual["id"] if actual else None) != body.expected_active_version_id:
        raise ApiError(409, 4002, "生效版本已变更", {"activeVersion": actual})
    await validate_publish(db, definition, product, record)
    now = datetime.now(UTC)
    if current is not None:
        await db.execute(table.update().where(table.c.id == current["id"]).values(status="2", update_time=now))
    await db.execute(table.update().where(table.c.id == id).values(
        status="1", published_at=now, publisher_id=actor, draft_token=None, update_time=now,
    ))
    published = (await db.execute(version_query(table).where(table.c.id == id))).mappings().one()
    result = dict(version_label(published, "id version status published_at"), activeVersion=active_summary(published))
    await commit(db)
    return result

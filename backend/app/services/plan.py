from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, case, func, literal, select

from app.models import plan as model, system
from app.models.basic import material
from app.services.basic import invalid
from app.services.changes import commit, record
from app.services.management import camel, filters, pagination, rows
from app.utils.responses import ApiError

ORDER = model.sales_order
ITEM = model.sales_order_item
PLAN = model.production_plan
SHANGHAI = timezone(timedelta(hours=8))
GANTT_MAX_DAYS = 92
GANTT_MAX_PLANS = 2000
CANCELLATION = "cancelled_at cancelled_by cancel_reason"
ITEM_FIELDS = (
    "id line_no product_id product_code product_name product_status unit_code "
    "unit_name order_qty due_date scheduled_qty available_qty completed_qty"
)
PLAN_FIELDS = "id plan_no order_no product_name planned_qty planned_start_at planned_end_at status"
REASONS = {
    "ORDER_CANCELLED": "销售订单已取消",
    "ORDER_HAS_ACTIVE_PLANS": "订单已有计划，无法执行此操作",
    "NO_AVAILABLE_QTY": "该订单行没有可排数量",
    "PLAN_CANCELLED": "生产计划已取消",
    "PLAN_ALREADY_TRANSFERRED": "生产计划已转工单",
    "MISSING_PRODUCTION_DEFINITION": "产品缺少生效的生产定义",
}


def serialize(row, fields):
    result = {}
    for field in fields.split():
        value = row[field]
        if value is not None and (field == "id" or field.endswith("_id") or field == "cancelled_by"):
            value = str(value)
        elif isinstance(value, Decimal):
            value = f"{value:.4f}"
        elif isinstance(value, datetime):
            value = value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        elif isinstance(value, date):
            value = value.isoformat()
        result[camel(field)] = value
    return result


def reason(code):
    return {"code": code, "message": REASONS[code]}


def conflict(code):
    detail = reason(code)
    raise ApiError(409, 4100, detail["message"], {"reason": detail})


def actions(**rules):
    result = {f"can{key[0].upper()}{key[1:]}": code is None for key, code in rules.items()}
    result["disableReasons"] = {key: reason(code) for key, code in rules.items() if code}
    return result


def check_dates(start, end):
    if start is not None and end is not None and end < start:
        raise invalid("dateEnd", "结束日期不得早于开始日期")


def time_window(statement, start, end):
    check_dates(start, end)
    if start is not None:
        statement = statement.where(PLAN.c.planned_end_at > datetime.combine(start, time.min, SHANGHAI))
    if end is not None and end < date.max:
        statement = statement.where(
            PLAN.c.planned_start_at < datetime.combine(end + timedelta(days=1), time.min, SHANGHAI),
        )
    return statement


def allocation():
    # The work-order module will supply completed quantity and closed-plan occupancy.
    return select(
        PLAN.c.order_item_id, func.sum(PLAN.c.planned_qty).label("occupied"),
    ).where(PLAN.c.cancelled_at.is_(None)).group_by(PLAN.c.order_item_id).subquery()


def order_query():
    occupied = allocation()
    covered = func.coalesce(occupied.c.occupied, 0) >= ITEM.c.order_qty
    stats = select(
        ITEM.c.order_id,
        func.count().label("item_count"),
        func.count().filter(covered).label("scheduled_item_count"),
    ).outerjoin(occupied, occupied.c.order_item_id == ITEM.c.id).group_by(ITEM.c.order_id).subquery()
    status = case(
        (ORDER.c.cancelled_at.is_not(None), "CANCELLED"),
        (stats.c.item_count == stats.c.scheduled_item_count, "SCHEDULED"),
        else_="PENDING_SCHEDULING",
    )
    return select(ORDER, stats.c.item_count, stats.c.scheduled_item_count, status.label("status")).join(
        stats, stats.c.order_id == ORDER.c.id,
    )


def item_query():
    occupied = allocation()
    unit = system.dict_data.alias("plan_unit")
    quantity = func.coalesce(occupied.c.occupied, Decimal(0))
    return select(
        ITEM, ORDER.c.order_no, ORDER.c.cancelled_at.label("order_cancelled"),
        ITEM.c.product_code_snapshot.label("product_code"),
        ITEM.c.product_name_snapshot.label("product_name"), material.c.status.label("product_status"),
        material.c.unit_code, unit.c.dict_label.label("unit_name"), quantity.label("scheduled_qty"),
        (ITEM.c.order_qty - quantity).label("available_qty"),
        literal(Decimal(0)).label("completed_qty"),
    ).join(ORDER, ORDER.c.id == ITEM.c.order_id).join(
        material, material.c.id == ITEM.c.product_id,
    ).join(unit, and_(unit.c.dict_code == material.c.unit_dict_code, unit.c.dict_value == material.c.unit_code)
    ).outerjoin(occupied, occupied.c.order_item_id == ITEM.c.id)


def item_action(row):
    if row["order_cancelled"]:
        return "ORDER_CANCELLED"
    if row["available_qty"] <= 0:
        return "NO_AVAILABLE_QTY"
    return None


def item_payload(row, *, candidate=False):
    fields = ITEM_FIELDS
    if candidate:
        fields = "order_id order_no " + fields.replace(" product_status", "").replace(" completed_qty", "")
    payload = serialize(row, fields)
    if candidate:
        payload["orderItemId"] = payload.pop("id")
    code = item_action(row)
    return dict(payload, canCreatePlan=code is None, disableReason=reason(code) if code else None)


async def list_orders(db, order_no, customer, status, start, end, page, size):
    check_dates(start, end)
    source = order_query().subquery()
    statement = filters(select(source), fuzzy=((source.c.order_no, order_no), (source.c.customer_name, customer)),
                        exact=((source.c.status, status),))
    if start is not None:
        statement = statement.where(source.c.order_date >= start)
    if end is not None:
        statement = statement.where(source.c.order_date <= end)
    total, results = await pagination(db, statement.order_by(source.c.order_date.desc(), source.c.id.desc()), page, size)
    fields = "id order_no customer_name order_date status item_count scheduled_item_count created_at"
    return {"total": total, "list": [serialize(row, fields) for row in results]}


async def one(db, statement):
    row = (await db.execute(statement)).mappings().one_or_none()
    if row is None:
        raise ApiError(404, 1002, "记录不存在")
    return row


async def order_detail(db, id):
    order = await one(db, order_query().where(ORDER.c.id == id))
    items = await rows(db, item_query().where(ITEM.c.order_id == id).order_by(ITEM.c.line_no))
    cancelled = "ORDER_CANCELLED" if order["cancelled_at"] else None
    active = any(item["scheduled_qty"] > 0 for item in items)
    capability = actions(
        edit=cancelled, cancel=cancelled or ("ORDER_HAS_ACTIVE_PLANS" if active else None),
        createPlan=cancelled or (None if any(item_action(item) is None for item in items) else "NO_AVAILABLE_QTY"),
    )
    return dict(serialize(order, "id order_no customer_name order_date remark status " + CANCELLATION),
                actions=capability, items=[item_payload(item) for item in items])


async def candidates(db, order_no, product_id, only_available, page, size):
    source = item_query().subquery()
    statement = filters(select(source), fuzzy=((source.c.order_no, order_no),),
                        exact=((source.c.product_id, product_id),))
    if only_available:
        statement = statement.where(source.c.order_cancelled.is_(None), source.c.available_qty > 0)
    total, results = await pagination(db, statement.order_by(source.c.order_id.desc(), source.c.line_no), page, size)
    return {"total": total, "list": [item_payload(row, candidate=True) for row in results]}


def plan_query():
    unit = system.dict_data.alias("schedule_unit")
    status = case((PLAN.c.cancelled_at.is_not(None), "CANCELLED"), else_="PENDING_TRANSFER")
    return select(
        PLAN, ORDER.c.order_no, ITEM.c.product_id, ITEM.c.product_code_snapshot.label("product_code"),
        ITEM.c.product_name_snapshot.label("product_name"), material.c.unit_code,
        unit.c.dict_label.label("unit_name"), status.label("status"),
    ).join(ITEM, ITEM.c.id == PLAN.c.order_item_id).join(ORDER, ORDER.c.id == ITEM.c.order_id).join(
        material, material.c.id == ITEM.c.product_id,
    ).join(unit, and_(unit.c.dict_code == material.c.unit_dict_code, unit.c.dict_value == material.c.unit_code))


def plan_payload(row):
    return dict(serialize(row, PLAN_FIELDS), workOrderNo=None, bomVersion=None, routingVersion=None)


async def plan_detail(db, id):
    row = await one(db, plan_query().where(PLAN.c.id == id))
    cancelled = "PLAN_CANCELLED" if row["cancelled_at"] else None
    capability = actions(reschedule=cancelled, cancel=cancelled, transfer=cancelled)
    capability["canTransfer"] = False
    return dict(plan_payload(row), **serialize(
        row, "order_item_id product_code unit_code unit_name remark " + CANCELLATION,
    ), actions=capability, features={"workOrderTransferEnabled": False}, workOrder=None)


async def list_plans(db, plan_no, order_no, product_id, status, start, end, page, size):
    source = time_window(plan_query(), start, end).subquery()
    statement = filters(select(source), fuzzy=((source.c.plan_no, plan_no), (source.c.order_no, order_no)),
                        exact=((source.c.product_id, product_id), (source.c.status, status)))
    total, results = await pagination(db, statement.order_by(source.c.planned_start_at, source.c.id), page, size)
    return {"total": total, "list": [plan_payload(row) for row in results]}


async def gantt(db, start, end, product_id):
    if (end - start).days >= GANTT_MAX_DAYS:
        raise invalid("dateEnd", f"甘特图查询最多包含 {GANTT_MAX_DAYS} 个自然日")
    statement = time_window(plan_query(), start, end)
    if product_id is not None:
        statement = statement.where(ITEM.c.product_id == product_id)
    result = []
    records = await rows(
        db, statement.order_by(PLAN.c.planned_start_at, PLAN.c.id).limit(GANTT_MAX_PLANS + 1),
    )
    if len(records) > GANTT_MAX_PLANS:
        raise invalid("dateEnd", f"匹配计划超过 {GANTT_MAX_PLANS} 条，请缩短日期范围或筛选产品")
    for row in records:
        value = serialize(row, "id plan_no order_no product_name planned_start_at planned_end_at status")
        value["planId"] = value.pop("id")
        value["startAt"] = value.pop("plannedStartAt")
        value["endAt"] = value.pop("plannedEndAt")
        result.append(dict(value, workOrderNo=None))
    return result


async def order_items(db, order_id):
    result = await rows(db, select(ITEM).where(ITEM.c.order_id == order_id).order_by(ITEM.c.id).with_for_update())
    return {item["id"]: item for item in result}


async def active_plans(db, ids):
    return await db.scalar(select(PLAN.c.id).where(
        PLAN.c.order_item_id.in_(ids), PLAN.c.cancelled_at.is_(None),
    ).limit(1)) is not None


async def save_order(db, actor, body, id=None):
    fields = body.model_dump(exclude={"items"})
    previous = {}
    if id is not None:
        order = await record(db, ORDER, id, lock=True)
        if order["cancelled_at"]:
            conflict("ORDER_CANCELLED")
        previous = await order_items(db, id)
    line_numbers = set()
    incoming = {}
    for index, item in enumerate(body.items):
        if item.line_no in line_numbers:
            raise invalid(f"items[{index}].lineNo", "行号不可重复")
        line_numbers.add(item.line_no)
        if item.id is not None:
            item_id = int(item.id)
            if item_id in incoming or item_id not in previous:
                raise invalid(f"items[{index}].id", "明细 ID 重复或不属于当前订单")
            incoming[item_id] = item

    if previous and await active_plans(db, previous):
        unchanged = (
            len(incoming) == len(previous) == len(body.items)
            and fields["customer_name"] == order["customer_name"] and fields["order_date"] == order["order_date"]
            and all(
                (item.line_no, int(item.product_id), item.order_qty, item.due_date) ==
                (old["line_no"], old["product_id"], old["order_qty"], old["due_date"])
                for item_id, item in incoming.items() for old in (previous[item_id],)
            )
        )
        if not unchanged:
            conflict("ORDER_HAS_ACTIVE_PLANS")
        await db.execute(ORDER.update().where(ORDER.c.id == id).values(
            remark=body.remark, updated_by=actor, updated_at=func.now(),
        ))
    else:
        if id is None:
            number = f"SO-{await db.scalar(select(model.order_numbers.next_value())):08d}"
            id = await db.scalar(ORDER.insert().values(
                **fields, order_no=number, created_by=actor, updated_by=actor,
            ).returning(ORDER.c.id))
        else:
            await db.execute(ORDER.update().where(ORDER.c.id == id).values(
                **fields, updated_by=actor, updated_at=func.now(),
            ))
        removed = previous.keys() - incoming.keys()
        if removed:
            # Cancelled schedules still reference their original order lines.
            if await db.scalar(select(PLAN.c.id).where(PLAN.c.order_item_id.in_(removed)).limit(1)):
                conflict("ORDER_HAS_ACTIVE_PLANS")
            await db.execute(ITEM.delete().where(ITEM.c.id.in_(removed)))
        for index, item in enumerate(body.items):
            old = previous.get(int(item.id)) if item.id else None
            data = item.model_dump(exclude={"id"})
            data["product_id"] = int(item.product_id)
            if not old or old["product_id"] != data["product_id"]:
                if old and await db.scalar(select(PLAN.c.id).where(PLAN.c.order_item_id == old["id"]).limit(1)):
                    conflict("ORDER_HAS_ACTIVE_PLANS")
                product = (await db.execute(select(material.c.code, material.c.name).where(
                    material.c.id == data["product_id"], material.c.is_product, material.c.status == "0",
                ).with_for_update(read=True))).one_or_none()
                if product is None:
                    raise invalid(f"items[{index}].productId", "请选择启用的成品")
                data.update(product_code_snapshot=product.code, product_name_snapshot=product.name)
            statement = ITEM.update().where(ITEM.c.id == old["id"]) if old else ITEM.insert()
            await db.execute(statement.values(**data, order_id=id))
    await commit(db)
    if not previous:
        return {"id": str(id), "orderNo": number}
    return await order_detail(db, id)


async def cancel_order(db, actor, id, body):
    order = await record(db, ORDER, id, lock=True)
    if order["cancelled_at"]:
        conflict("ORDER_CANCELLED")
    if await active_plans(db, await order_items(db, id)):
        conflict("ORDER_HAS_ACTIVE_PLANS")
    await mark_cancelled(db, ORDER, id, actor, body)
    return await order_detail(db, id)


async def mark_cancelled(db, table, id, actor, body):
    await db.execute(table.update().where(table.c.id == id).values(
        cancelled_at=func.now(), cancelled_by=actor, cancel_reason=body.cancel_reason,
        updated_by=actor, updated_at=func.now(),
    ))
    await commit(db)


async def lock_source(db, item_id):
    owner = await db.scalar(select(ITEM.c.order_id).where(ITEM.c.id == item_id))
    if owner is None:
        raise ApiError(404, 1002, "订单明细不存在")
    order = await record(db, ORDER, owner, lock=True)
    if order["cancelled_at"]:
        conflict("ORDER_CANCELLED")
    return await record(db, ITEM, item_id, lock=True)


async def lock_plan(db, id):
    snapshot = await record(db, PLAN, id)
    item = await lock_source(db, snapshot["order_item_id"])
    plan = await record(db, PLAN, id, lock=True)
    if plan["cancelled_at"]:
        conflict("PLAN_CANCELLED")
    return item, plan


async def save_plan(db, actor, body, id=None):
    if body.planned_end_at <= body.planned_start_at:
        raise invalid("plannedEndAt", "结束时间必须晚于开始时间")
    if id is None:
        item = await lock_source(db, int(body.order_item_id))
        current = Decimal(0)
    else:
        item, plan = await lock_plan(db, id)
        current = plan["planned_qty"]
    occupied = await db.scalar(select(func.coalesce(func.sum(PLAN.c.planned_qty), 0)).where(
        PLAN.c.order_item_id == item["id"], PLAN.c.cancelled_at.is_(None),
    ))
    available = item["order_qty"] - occupied + current
    if body.planned_qty > available:
        raise ApiError(409, "PLAN_QUANTITY_EXCEEDS_AVAILABLE", "计划数量超过可排数量", {
            "orderItemId": str(item["id"]), "orderQty": f'{item["order_qty"]:.4f}',
            "scheduledQty": f"{occupied - current:.4f}", "availableQty": f"{available:.4f}",
        })
    fields = body.model_dump(exclude={"order_item_id"})
    if id is None:
        number = f"PP-{await db.scalar(select(model.plan_numbers.next_value())):08d}"
        id = await db.scalar(PLAN.insert().values(
            **fields, plan_no=number, order_item_id=item["id"], created_by=actor, updated_by=actor,
        ).returning(PLAN.c.id))
        await commit(db)
        return {"id": str(id), "planNo": number}
    await db.execute(PLAN.update().where(PLAN.c.id == id).values(
        **fields, updated_by=actor, updated_at=func.now(),
    ))
    await commit(db)
    return await plan_detail(db, id)


async def cancel_plan(db, actor, id, body):
    await lock_plan(db, id)
    await mark_cancelled(db, PLAN, id, actor, body)
    return await plan_detail(db, id)


async def transfer_plan(db, id):
    await record(db, PLAN, id)
    raise ApiError(409, 4100, "工单转单功能尚未启用", {
        "reason": {"code": "WORK_ORDER_TRANSFER_DISABLED", "message": "工单转单功能尚未启用"},
    })

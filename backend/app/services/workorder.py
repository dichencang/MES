from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP, localcontext

from sqlalchemy import func, or_, select

from app.models import basic, system, workorder as model
from app.services import plan
from app.services.basic import invalid, material_query, module_lock
from app.services.changes import commit, record
from app.services.management import filters, pagination, rows
from app.utils.responses import ApiError

ORDER = model.work_order
STEP = model.step
MATERIAL = model.work_material
ASSIGNMENT = model.assignment
EVENT = model.event
USER = system.user
ROW_FIELDS = (
    "id work_order_no product_id product_code product_name unit_code unit_name planned_qty "
    "planned_start_at planned_end_at status plan_id plan_no released_at started_at step_count"
)
MATERIAL_FIELDS = (
    "id material_id material_code material_name unit_code unit_name base_qty component_qty "
    "required_qty sort_no source_bom_item_id"
)
EVENT_FIELDS = "id action from_status to_status operator_name occurred_at reason"
REASONS = {
    "WORK_ORDER_CANCELLED": "工单已撤销",
    "WORK_ORDER_NOT_RELEASED": "工单尚未下发",
    "WORK_ORDER_ALREADY_RELEASED": "工单已下发",
    "WORK_ORDER_ALREADY_STARTED": "工单已开工",
    "WORK_ORDER_STEP_STARTED": "该工序已开工",
    "WORK_ORDER_TERMINAL": "工单已完成或关闭",
    "PLAN_LINKED_WORK_ORDER": "计划转入的工单不可编辑",
    "PLAN_CANCELLED": "来源计划已取消",
    "WORK_ORDER_SETTLEMENT_DISABLED": "完工及关闭尚未开放",
}


def reason(code):
    return {"code": code, "message": REASONS[code]} if code else None


def rules(order):
    status = order["status"]
    stop = {"CANCELLED": "WORK_ORDER_CANCELLED", "COMPLETED": "WORK_ORDER_TERMINAL",
            "CLOSED": "WORK_ORDER_TERMINAL"}.get(status)
    released = None if status == "PENDING_RELEASE" else "WORK_ORDER_ALREADY_RELEASED"
    started = "WORK_ORDER_ALREADY_STARTED" if status == "IN_PRODUCTION" else None
    return {
        "edit": stop or ("PLAN_LINKED_WORK_ORDER" if order["plan_id"] else released),
        "release": stop or released,
        "assign": stop,
        "start": stop or started or ("WORK_ORDER_NOT_RELEASED" if status == "PENDING_RELEASE" else None),
        "cancel": stop or started,
        "complete": "WORK_ORDER_SETTLEMENT_DISABLED",
        "close": "WORK_ORDER_SETTLEMENT_DISABLED",
    }


def require_action(code):
    if code:
        detail = reason(code)
        raise ApiError(409, 4100, detail["message"], {"reason": detail})


def query():
    count = select(func.count()).select_from(STEP).where(STEP.c.work_order_id == ORDER.c.id)
    return select(
        ORDER, plan.PLAN.c.plan_no, count.scalar_subquery().label("step_count"),
        basic.bom.c.version.label("bom_version"), basic.routing.c.version.label("routing_version"),
    ).outerjoin(plan.PLAN, plan.PLAN.c.id == ORDER.c.plan_id
    ).join(basic.bom, basic.bom.c.id == ORDER.c.bom_id
    ).join(basic.routing, basic.routing.c.id == ORDER.c.routing_id)


def row_payload(row):
    return dict(plan.serialize(row, ROW_FIELDS), finishedStepCount=None)


def event_query(id):
    return select(EVENT).where(EVENT.c.work_order_id == id).order_by(
        EVENT.c.occurred_at.desc(), EVENT.c.id.desc(),
    )


async def detail(db, id):
    order = await plan.one(db, query().where(ORDER.c.id == id))
    material_rows = await rows(db, select(MATERIAL).where(
        MATERIAL.c.work_order_id == id).order_by(MATERIAL.c.sort_no, MATERIAL.c.id))
    step_rows = await rows(db, select(STEP).where(
        STEP.c.work_order_id == id).order_by(STEP.c.seq, STEP.c.id))
    assignment_rows = await rows(db, select(ASSIGNMENT).join(STEP).where(
        STEP.c.work_order_id == id).order_by(ASSIGNMENT.c.assigned_at.desc(), ASSIGNMENT.c.id.desc()))
    grouped = defaultdict(list)
    for row in assignment_rows:
        grouped[row["work_order_step_id"]].append(plan.serialize(
            row, "id assignee_id assignee_name assigned_at ended_at",
        ))
    order_rules = rules(order)
    steps = []
    for step in step_rows:
        code = order_rules["assign"] or ("WORK_ORDER_STEP_STARTED" if step["started_at"] else None)
        steps.append(dict(plan.serialize(step, "id seq process_id process_code process_name source_routing_step_id remark"),
                          canAssign=code is None, disableReason=reason(code), assignees=grouped[step["id"]]))
    if not order_rules["assign"] and steps and not any(step["canAssign"] for step in steps):
        order_rules["assign"] = "WORK_ORDER_STEP_STARTED"
    actions = {f"can{action.title()}": code is None for action, code in order_rules.items()}
    actions["canAssign"] = any(step["canAssign"] for step in steps)
    actions["disableReasons"] = {action: reason(code) for action, code in order_rules.items() if code}
    metadata = plan.serialize(order, "remark cancelled_at cancelled_by cancel_reason closed_at close_reason")
    return dict(row_payload(order), **metadata, closedBy=str(order["closed_by"]) if order["closed_by"] else None,
                bomVersion={"id": str(order["bom_id"]), "version": order["bom_version"]},
                routingVersion={"id": str(order["routing_id"]), "version": order["routing_version"]},
                currentStepId=None, actions=actions, steps=steps,
                materials=[plan.serialize(row, MATERIAL_FIELDS) for row in material_rows],
                events=[plan.serialize(row, EVENT_FIELDS) for row in await rows(db, event_query(id).limit(10))])


async def listing(db, number, plan_no, product_id, status, start, end, page, size):
    statement = filters(plan.time_window(query(), start, end, ORDER), fuzzy=((ORDER.c.work_order_no, number),
                        (plan.PLAN.c.plan_no, plan_no)), exact=((ORDER.c.product_id, product_id), (ORDER.c.status, status)))
    total, result = await pagination(db, statement.order_by(ORDER.c.planned_start_at, ORDER.c.id), page, size)
    return {"total": total, "list": [row_payload(row) for row in result]}


async def gantt(db, start, end, product_id):
    if (end - start).days >= plan.GANTT_MAX_DAYS:
        raise invalid("dateEnd", f"甘特图查询最多包含 {plan.GANTT_MAX_DAYS} 个自然日")
    statement = plan.time_window(select(
        ORDER.c.id, ORDER.c.work_order_no, ORDER.c.product_name, ORDER.c.planned_start_at,
        ORDER.c.planned_end_at, ORDER.c.status, plan.PLAN.c.plan_no,
    ).outerjoin(plan.PLAN, plan.PLAN.c.id == ORDER.c.plan_id), start, end, ORDER)
    statement = filters(statement, exact=((ORDER.c.product_id, product_id),))
    result = await rows(db, statement.order_by(ORDER.c.planned_start_at, ORDER.c.id).limit(plan.GANTT_MAX_PLANS + 1))
    if len(result) > plan.GANTT_MAX_PLANS:
        raise invalid("dateEnd", f"匹配工单超过 {plan.GANTT_MAX_PLANS} 条，请缩短日期范围或筛选产品")
    fields = "id work_order_no product_name planned_start_at planned_end_at status plan_no"
    return [plan.serialize(row, fields) for row in result]


def employees():
    return select(USER.c.id, USER.c.username, USER.c.real_name).where(
        USER.c.status == "0", USER.c.del_flag == "0",
    )


async def options(db, keyword, page, size):
    statement = employees()
    if keyword:
        statement = statement.where(or_(USER.c.username.icontains(keyword, autoescape=True),
                                        USER.c.real_name.icontains(keyword, autoescape=True)))
    total, result = await pagination(db, statement.order_by(USER.c.real_name, USER.c.id), page, size)
    return {"total": total, "list": [plan.serialize(row, "id username real_name") for row in result]}


async def events(db, id, page, size):
    await record(db, ORDER, id)
    total, result = await pagination(db, event_query(id), page, size)
    return {"total": total, "list": [plan.serialize(row, EVENT_FIELDS) for row in result]}


async def event(db, id, actor, action, to_status, from_status=None, message=None):
    name = await db.scalar(select(USER.c.real_name).where(USER.c.id == actor))
    await db.execute(EVENT.insert().values(
        work_order_id=id, operator_id=actor, operator_name=name, action=action,
        from_status=from_status, to_status=to_status, reason=message,
    ))


async def active_definitions(db, product_id):
    # Publishing and material archive changes use the same advisory lock.
    await module_lock(db)
    definitions = {}
    for name, table in (("BOM", basic.bom), ("ROUTING", basic.routing)):
        definitions[name] = (await db.execute(select(table).where(
            table.c.product_id == product_id, table.c.status == "1",
        ))).mappings().one_or_none()
    return definitions


def missing_definitions(product_id, definitions):
    missing = [name for name, value in definitions.items() if value is None]
    if missing:
        raise ApiError(409, "MISSING_PRODUCTION_DEFINITION", "产品缺少生效的生产定义",
                       {"productId": str(product_id), "missingItems": missing})


def required_qty(item, quantity):
    with localcontext() as context:
        context.prec = 60
        result = (item["component_qty"] * quantity / item["base_qty"]).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP,
        )
    if result <= 0 or result >= Decimal("100000000000000"):
        raise ApiError(409, "WORK_ORDER_QUANTITY_INVALID", "工单子件需求量舍入为零或超出范围", {
            "field": "plannedQty", "materialId": str(item["material_id"]),
            "materialCode": item["material_code"], "materialName": item["material_name"],
            "sourceBomItemId": str(item["source_bom_item_id"]),
            "reason": "ROUNDED_TO_ZERO" if result <= 0 else "OVERFLOW",
        })
    return result


def validate_times(fields):
    if fields["planned_end_at"] <= fields["planned_start_at"]:
        raise invalid("plannedEndAt", "结束时间必须晚于开始时间")


async def create(db, actor, product_id, fields, *, plan_id=None, number=None):
    validate_times(fields)
    definitions = await active_definitions(db, product_id)
    product = (await db.execute(material_query().where(
        basic.material.c.id == product_id, basic.material.c.is_product, basic.material.c.status == "0",
    ))).mappings().one_or_none()
    if product is None:
        raise invalid("productId", "请选择启用的成品")
    missing_definitions(product_id, definitions)
    bom, routing = definitions["BOM"], definitions["ROUTING"]
    item = basic.bom_item
    archive = material_query().subquery()
    components = await rows(db, select(
        item.c.id.label("source_bom_item_id"), item.c.material_id, archive.c.code.label("material_code"),
        archive.c.name.label("material_name"), archive.c.unit_code, archive.c.unit_name,
        item.c.qty.label("component_qty"), item.c.sort_no,
    ).join(archive, archive.c.id == item.c.material_id).where(item.c.bom_id == bom["id"]))
    materials = []
    for component in components:
        snapshot = dict(component, base_qty=bom["base_qty"])
        materials.append(dict(snapshot, required_qty=required_qty(snapshot, fields["planned_qty"])))
    route = basic.routing_step
    steps = await rows(db, select(
        route.c.id.label("source_routing_step_id"), route.c.process_id, route.c.seq, route.c.remark,
        basic.process.c.code.label("process_code"), basic.process.c.name.label("process_name"),
    ).join(basic.process).where(route.c.routing_id == routing["id"]))
    if number is None:
        number = f"WO-{await db.scalar(select(model.numbers.next_value())):08d}"
    id = await db.scalar(ORDER.insert().values(
        **fields, work_order_no=number, plan_id=plan_id, product_id=product_id,
        product_code=product["code"], product_name=product["name"],
        unit_code=product["unit_code"], unit_name=product["unit_name"],
        bom_id=bom["id"], routing_id=routing["id"], created_by=actor, updated_by=actor,
    ).returning(ORDER.c.id))
    if materials:
        await db.execute(MATERIAL.insert(), [dict(row, work_order_id=id) for row in materials])
    if steps:
        await db.execute(STEP.insert(), [dict(row, work_order_id=id) for row in steps])
    await event(db, id, actor, "TRANSFER" if plan_id else "CREATE", "PENDING_RELEASE")
    return {"id": str(id), "workOrderNo": number}


async def create_manual(db, actor, body):
    result = await create(db, actor, int(body.product_id), body.model_dump(exclude={"product_id"}))
    await commit(db)
    return result


async def locked_order(db, id):
    order = await record(db, ORDER, id)
    if order["plan_id"]:
        await plan.lock_plan(db, order["plan_id"])
    return await record(db, ORDER, id, lock=True)


async def update(db, actor, id, body):
    order = await locked_order(db, id)
    require_action(rules(order)["edit"])
    fields = body.model_dump()
    validate_times(fields)
    for material in await rows(db, select(MATERIAL).where(MATERIAL.c.work_order_id == id)):
        await db.execute(MATERIAL.update().where(MATERIAL.c.id == material["id"]).values(
            required_qty=required_qty(material, body.planned_qty),
        ))
    await db.execute(ORDER.update().where(ORDER.c.id == id).values(**fields, updated_by=actor, updated_at=func.now()))
    await event(db, id, actor, "UPDATE", order["status"], order["status"])
    await commit(db)
    return await detail(db, id)


async def transition(db, actor, id, action, cancel_reason=None):
    order = await locked_order(db, id)
    require_action(rules(order)[action])
    target, prefix = {"release": ("RELEASED", "released"), "start": ("IN_PRODUCTION", "started"),
                      "cancel": ("CANCELLED", "cancelled")}[action]
    fields = {"status": target, f"{prefix}_at": func.now(), f"{prefix}_by": actor,
              "updated_at": func.now(), "updated_by": actor}
    if cancel_reason is not None:
        fields["cancel_reason"] = cancel_reason
    await db.execute(ORDER.update().where(ORDER.c.id == id).values(**fields))
    await event(db, id, actor, action.upper(), target, order["status"], cancel_reason)
    await commit(db)
    return await detail(db, id)


async def assign(db, actor, id, step_id, body):
    order = await locked_order(db, id)
    require_action(rules(order)["assign"])
    step = await plan.one(db, select(STEP).where(STEP.c.id == step_id, STEP.c.work_order_id == id))
    require_action("WORK_ORDER_STEP_STARTED" if step["started_at"] else None)
    target = {int(value) for value in body.assignee_ids}
    active = {row["assignee_id"] for row in await rows(db, select(ASSIGNMENT.c.assignee_id).where(
        ASSIGNMENT.c.work_order_step_id == step_id, ASSIGNMENT.c.ended_at.is_(None),
    ))}
    if active == target:
        await commit(db)
        return await detail(db, id)
    found = await rows(db, employees().where(USER.c.id.in_(target)).with_for_update(read=True))
    if len(found) != len(target):
        raise invalid("assigneeIds", "请选择启用且未删除的员工")
    removed = active - target
    if removed:
        await db.execute(ASSIGNMENT.update().where(
            ASSIGNMENT.c.work_order_step_id == step_id, ASSIGNMENT.c.ended_at.is_(None),
            ASSIGNMENT.c.assignee_id.in_(removed),
        ).values(ended_at=func.now(), ended_by=actor))
    added = [dict(work_order_step_id=step_id, assignee_id=user["id"], assignee_name=user["real_name"],
                  assigned_by=actor) for user in found if user["id"] not in active]
    if added:
        await db.execute(ASSIGNMENT.insert(), added)
    await event(db, id, actor, "ASSIGN", order["status"], order["status"])
    await commit(db)
    return await detail(db, id)

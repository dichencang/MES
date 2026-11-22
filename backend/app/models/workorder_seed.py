from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.models import basic, plan, system, workorder
from app.models.basic_seed import permission_insert

ACTIONS = (
    ("create", "新建"), ("update", "编辑"), ("release", "下发"), ("assign", "派工"),
    ("start", "开工"), ("cancel", "撤销"), ("close", "关闭"), ("complete", "完成"),
)


def permission_statements():
    yield permission_insert("workorder", "workorder:list", "工单列表", "MENU", 1,
                            path="/workorder/list", component="workorder/list/index", icon="Tickets")
    yield permission_insert("workorder", "workorder:gantt:list", "工单甘特图", "MENU", 2,
                            path="/workorder/gantt", component="workorder/gantt/index", icon="Calendar")
    for index, (action, title) in enumerate(ACTIONS, 1):
        yield permission_insert("workorder:list", f"workorder:{action}", title, "BUTTON", index)


async def seed_sample(db):
    from app.services.workorder import create

    table = workorder.work_order
    actor = await db.scalar(select(system.user.c.id).where(system.user.c.username == "admin"))
    if actor is None:
        return
    existing_product = await db.scalar(select(table.c.product_id).where(table.c.work_order_no == "WO-SAMPLE"))
    if existing_product is not None:
        await seed_transfer_sample(db, actor, existing_product)
        return
    product_id = await fixture_archive(db, basic.material, "WO-DEMO", "工单联调成品",
                                       category_code="FINISHED", unit_code="PCS", is_product=True)
    component_id = await fixture_archive(db, basic.material, "WO-DEMO-PART", "工单联调子件",
                                         category_code="RAW", unit_code="PCS", is_product=False)
    process_id = await fixture_archive(db, basic.process, "WO-DEMO-STEP", "联调装配")
    for definition, lines, counter, fields in (
        (basic.bom, basic.bom_item, "bom_max_version",
         {"material_id": component_id, "qty": Decimal("2"), "sort_no": 1}),
        (basic.routing, basic.routing_step, "routing_max_version", {"process_id": process_id, "seq": 1}),
    ):
        active = await db.scalar(select(definition.c.id).where(
            definition.c.product_id == product_id, definition.c.status == "1",
        ))
        if active is None:
            version = await db.scalar(basic.material.update().where(basic.material.c.id == product_id)
                                      .values({counter: basic.material.c[counter] + 1})
                                      .returning(basic.material.c[counter]))
            active = await db.scalar(definition.insert().values(
                product_id=product_id, version=version, status="1", last_editor_id=actor,
                published_at=func.now(), publisher_id=actor,
            ).returning(definition.c.id))
            foreign_key = f"{definition.name.removeprefix('basic_')}_id"
            await db.execute(lines.insert().values(**fields, **{foreign_key: active}))
    await create(db, actor, product_id, {
        "planned_qty": Decimal("20"), "planned_start_at": datetime(2026, 11, 23, 0, tzinfo=UTC),
        "planned_end_at": datetime(2026, 11, 23, 9, tzinfo=UTC), "remark": "本地工单联调样例",
    }, number="WO-SAMPLE")
    await seed_transfer_sample(db, actor, product_id)


async def fixture_archive(db, table, code, name, **fields):
    await db.execute(insert(table).values(code=code, name=name, **fields).on_conflict_do_nothing(
        index_elements=[table.c.code],
    ))
    return await db.scalar(select(table.c.id).where(table.c.code == code))


async def seed_transfer_sample(db, actor, product_id):
    order, item, schedule = plan.sales_order, plan.sales_order_item, plan.production_plan
    order_id = await db.scalar(insert(order).values(
        order_no="SO-WO-SAMPLE", customer_name="工单转单样例客户", order_date=date(2026, 11, 22),
        created_by=actor, updated_by=actor,
    ).on_conflict_do_nothing(index_elements=[order.c.order_no]).returning(order.c.id))
    if order_id is None:
        return
    product = (await db.execute(select(basic.material.c.code, basic.material.c.name).where(
        basic.material.c.id == product_id,
    ))).one()
    item_id = await db.scalar(item.insert().values(
        order_id=order_id, line_no=1, product_id=product_id, order_qty=Decimal("30"),
        product_code_snapshot=product.code, product_name_snapshot=product.name, due_date=date(2026, 11, 28),
    ).returning(item.c.id))
    await db.execute(schedule.insert().values(
        plan_no="PP-WO-SAMPLE", order_item_id=item_id, planned_qty=Decimal("30"),
        planned_start_at=datetime(2026, 11, 24, 0, tzinfo=UTC),
        planned_end_at=datetime(2026, 11, 24, 9, tzinfo=UTC), created_by=actor, updated_by=actor,
    ))

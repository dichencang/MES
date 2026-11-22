"""Plan management permissions and a local acceptance sample."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models import plan, system
from app.models.basic import material
from app.models.basic_seed import permission_insert

MENUS = (
    ("sales-order", "销售订单", "Tickets", (("create", "新建"), ("update", "编辑"), ("cancel", "取消"))),
    ("production-plan", "生产计划", "Calendar", (("create", "新建"), ("update", "编辑"),
                                                  ("cancel", "取消"), ("transfer", "转工单"))),
    ("gantt", "计划甘特图", "DataAnalysis", ()),
)


def permission_statements():
    for position, (resource, title, icon, actions) in enumerate(MENUS, 1):
        prefix = f"plan:{resource}"
        menu = f"{prefix}:list"
        yield permission_insert(
            "plan", menu, title, "MENU", position,
            path=f"/plan/{resource}", component=f"plan/{resource}/index", icon=icon,
        )
        for order, (action, label) in enumerate(actions, 1):
            yield permission_insert(menu, f"{prefix}:{action}", label, "BUTTON", order)


async def seed_sample(connection):
    order, item, schedule = plan.sales_order, plan.sales_order_item, plan.production_plan
    product = (await connection.execute(
        select(material.c.id, material.c.code, material.c.name)
        .where(material.c.is_product, material.c.status == "0").order_by(material.c.id).limit(1)
    )).one_or_none()
    actor = await connection.scalar(select(system.user.c.id).where(system.user.c.username == "admin"))
    if actor is None:
        return
    if product is None:
        await connection.execute(insert(material).values(
            code="PLAN-DEMO", name="计划联调成品", category_code="FINISHED", unit_code="PCS", is_product=True,
        ).on_conflict_do_nothing(index_elements=[material.c.code]))
        product = (await connection.execute(
            select(material.c.id, material.c.code, material.c.name).where(material.c.code == "PLAN-DEMO")
        )).one()
    order_id = await connection.scalar(insert(order).values(
        order_no="SO-SAMPLE", customer_name="联调样例客户", order_date=date(2026, 11, 22),
        created_by=actor, updated_by=actor,
    ).on_conflict_do_nothing(index_elements=[order.c.order_no]).returning(order.c.id))
    if order_id is None:
        return
    item_id = await connection.scalar(item.insert().values(
        order_id=order_id, line_no=1, product_id=product.id, product_code_snapshot=product.code,
        product_name_snapshot=product.name, order_qty=Decimal("100"), due_date=date(2026, 11, 28),
    ).returning(item.c.id))
    await connection.execute(schedule.insert().values(
        plan_no="PP-SAMPLE", order_item_id=item_id, planned_qty=Decimal("60"),
        planned_start_at=datetime(2026, 11, 23, 0, tzinfo=UTC),
        planned_end_at=datetime(2026, 11, 23, 9, tzinfo=UTC), created_by=actor, updated_by=actor,
    ))

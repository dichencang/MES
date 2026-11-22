"""Work orders, production snapshots, assignments and timeline."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Numeric, Sequence, String, Text, UniqueConstraint

from app.models import basic, plan, system

numbers = Sequence("prod_work_order_number_seq", metadata=system.metadata)
STATUSES = ("PENDING_RELEASE", "RELEASED", "IN_PRODUCTION", "COMPLETED", "CLOSED", "CANCELLED")


def ref(name, target, *, nullable=False, index=False):
    return Column(name, ForeignKey(target, ondelete="RESTRICT"), nullable=nullable, index=index)


def product_snapshot(prefix):
    return (
        Column(f"{prefix}_code", String(50), nullable=False),
        Column(f"{prefix}_name", String(100), nullable=False),
        Column("unit_code", String(64), nullable=False),
        Column("unit_name", String(100), nullable=False),
    )


work_order = system.entity(
    "prod_work_order",
    Column("work_order_no", String(40), nullable=False, unique=True),
    ref("plan_id", plan.production_plan.c.id, nullable=True),
    ref("product_id", basic.material.c.id, index=True),
    *product_snapshot("product"),
    Column("planned_qty", Numeric(18, 4), nullable=False),
    system.timestamp("planned_start_at", default=False),
    system.timestamp("planned_end_at", default=False),
    Column("status", String(24), nullable=False, server_default="PENDING_RELEASE"),
    ref("bom_id", basic.bom.c.id),
    ref("routing_id", basic.routing.c.id),
    system.timestamp("released_at", nullable=True, default=False),
    ref("released_by", system.user.c.id, nullable=True),
    system.timestamp("started_at", nullable=True, default=False),
    ref("started_by", system.user.c.id, nullable=True),
    system.timestamp("completed_at", nullable=True, default=False),
    system.timestamp("closed_at", nullable=True, default=False),
    ref("closed_by", system.user.c.id, nullable=True),
    Column("close_reason", String(200)),
    *plan.document_fields(),
    CheckConstraint("planned_qty > 0"),
    CheckConstraint("planned_end_at > planned_start_at"),
    CheckConstraint("status IN " + repr(STATUSES)),
    CheckConstraint("(status = 'CANCELLED') = (cancelled_at IS NOT NULL)"),
)
Index("ix_prod_work_order_start_id", work_order.c.planned_start_at, work_order.c.id)
Index("ix_prod_work_order_plan", work_order.c.plan_id)
Index("uq_prod_work_order_active_plan", work_order.c.plan_id, unique=True,
      postgresql_where=work_order.c.plan_id.is_not(None) & (work_order.c.status != "CANCELLED"))

work_material = system.entity(
    "prod_work_order_material",
    ref("work_order_id", work_order.c.id),
    ref("source_bom_item_id", basic.bom_item.c.id),
    ref("material_id", basic.material.c.id),
    *product_snapshot("material"),
    Column("base_qty", Numeric(18, 4), nullable=False),
    Column("component_qty", Numeric(18, 4), nullable=False),
    Column("required_qty", Numeric(18, 4), nullable=False),
    Column("sort_no", Integer, nullable=False),
    UniqueConstraint("work_order_id", "source_bom_item_id"),
    CheckConstraint("base_qty > 0 AND component_qty > 0 AND required_qty > 0"),
)

step = system.entity(
    "prod_work_order_step",
    ref("work_order_id", work_order.c.id),
    ref("source_routing_step_id", basic.routing_step.c.id),
    ref("process_id", basic.process.c.id),
    Column("process_code", String(50), nullable=False),
    Column("process_name", String(100), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("remark", Text),
    system.timestamp("started_at", nullable=True, default=False),
    UniqueConstraint("work_order_id", "source_routing_step_id"),
)

assignment = system.entity(
    "prod_work_order_assignment",
    ref("work_order_step_id", step.c.id, index=True),
    ref("assignee_id", system.user.c.id),
    Column("assignee_name", String(64), nullable=False),
    ref("assigned_by", system.user.c.id),
    system.timestamp("assigned_at"),
    ref("ended_by", system.user.c.id, nullable=True),
    system.timestamp("ended_at", nullable=True, default=False),
    CheckConstraint("(ended_at IS NULL) = (ended_by IS NULL)"),
)
Index("uq_prod_work_order_active_assignee", assignment.c.work_order_step_id, assignment.c.assignee_id,
      unique=True, postgresql_where=assignment.c.ended_at.is_(None))

event = system.entity(
    "prod_work_order_event",
    ref("work_order_id", work_order.c.id),
    Column("action", String(24), nullable=False),
    Column("from_status", String(24)),
    Column("to_status", String(24), nullable=False),
    ref("operator_id", system.user.c.id),
    Column("operator_name", String(64), nullable=False),
    system.timestamp("occurred_at"),
    Column("reason", Text),
)
Index("ix_prod_work_order_event_timeline", event.c.work_order_id, event.c.occurred_at, event.c.id)

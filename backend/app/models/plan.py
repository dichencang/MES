"""Sales orders and production scheduling."""

from sqlalchemy import (
    CheckConstraint, Column, Date, ForeignKey, Index, Integer,
    Numeric, Sequence, String, Text, UniqueConstraint,
)

from app.models.basic import material
from app.models.system import entity, metadata, timestamp, user

order_numbers = Sequence("plan_sales_order_number_seq", metadata=metadata)
plan_numbers = Sequence("plan_production_plan_number_seq", metadata=metadata)


def document_fields():
    return (
        Column("remark", Text),
        Column("created_by", ForeignKey(user.c.id, ondelete="RESTRICT"), nullable=False),
        Column("updated_by", ForeignKey(user.c.id, ondelete="RESTRICT"), nullable=False),
        timestamp("created_at"),
        timestamp("updated_at"),
        timestamp("cancelled_at", nullable=True, default=False),
        Column("cancelled_by", ForeignKey(user.c.id, ondelete="RESTRICT")),
        Column("cancel_reason", Text),
        CheckConstraint(
            "(cancelled_at IS NULL AND cancelled_by IS NULL AND cancel_reason IS NULL)"
            " OR (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL"
            " AND cancel_reason IS NOT NULL AND btrim(cancel_reason) <> '')"
        ),
    )


sales_order = entity(
    "plan_sales_order",
    Column("order_no", String(40), nullable=False, unique=True),
    Column("customer_name", Text, nullable=False),
    Column("order_date", Date, nullable=False),
    *document_fields(),
    CheckConstraint("btrim(customer_name) <> ''"),
)
Index("ix_plan_sales_order_date_id", sales_order.c.order_date, sales_order.c.id)

sales_order_item = entity(
    "plan_sales_order_item",
    Column("order_id", ForeignKey(sales_order.c.id, ondelete="RESTRICT"), nullable=False),
    Column("line_no", Integer, nullable=False),
    Column("product_id", ForeignKey(material.c.id, ondelete="RESTRICT"), nullable=False, index=True),
    Column("product_code_snapshot", String(50), nullable=False),
    Column("product_name_snapshot", String(100), nullable=False),
    Column("order_qty", Numeric(18, 4), nullable=False),
    Column("due_date", Date, nullable=False),
    CheckConstraint("line_no > 0"),
    CheckConstraint("order_qty > 0"),
    UniqueConstraint("order_id", "line_no", deferrable=True, initially="DEFERRED"),
)

production_plan = entity(
    "plan_production_plan",
    Column("plan_no", String(40), nullable=False, unique=True),
    Column("order_item_id", ForeignKey(sales_order_item.c.id, ondelete="RESTRICT"),
           nullable=False, index=True),
    Column("planned_qty", Numeric(18, 4), nullable=False),
    timestamp("planned_start_at", default=False),
    timestamp("planned_end_at", default=False),
    *document_fields(),
    CheckConstraint("planned_qty > 0"),
    CheckConstraint("planned_end_at > planned_start_at"),
)
Index("ix_plan_production_plan_start_id", production_plan.c.planned_start_at, production_plan.c.id)

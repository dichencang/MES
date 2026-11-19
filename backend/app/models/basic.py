"""Master data and versioned production definitions."""

from sqlalchemy import (
    Boolean, CHAR, CheckConstraint, Column, Computed, ForeignKey,
    ForeignKeyConstraint, Index, Integer, Numeric, String, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.models.system import entity, flag, timestamp


material = entity(
    "basic_material",
    Column("code", String(50), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("category_code", String(64), nullable=False),
    Column("unit_code", String(64), nullable=False),
    Column("category_dict_code", String(64), Computed("'material_category'", persisted=True), nullable=False),
    Column("unit_dict_code", String(64), Computed("'material_unit'", persisted=True), nullable=False),
    Column("spec", String(100)),
    Column("remark", String(200)),
    flag("status"),
    Column("is_product", Boolean, nullable=False),
    Column("bom_max_version", Integer, nullable=False, server_default="0"),
    Column("routing_max_version", Integer, nullable=False, server_default="0"),
    CheckConstraint("code ~ '^[A-Za-z0-9_-]+$'"),
    CheckConstraint("bom_max_version >= 0 AND routing_max_version >= 0"),
    ForeignKeyConstraint(
        ("category_dict_code", "category_code"), ("sys_dict_data.dict_code", "sys_dict_data.dict_value"),
        onupdate="RESTRICT", ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ("unit_dict_code", "unit_code"), ("sys_dict_data.dict_code", "sys_dict_data.dict_value"),
        onupdate="RESTRICT", ondelete="RESTRICT",
    ),
)

process = entity(
    "basic_process",
    Column("code", String(50), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("description", String(200)),
    flag("status"),
    CheckConstraint("code ~ '^[A-Za-z0-9_-]+$'"),
)


def version_table(name, *fields):
    return entity(
        name,
        Column("product_id", ForeignKey(material.c.id, ondelete="RESTRICT"), nullable=False),
        Column("version", Integer, nullable=False),
        Column("status", CHAR(1), nullable=False, server_default="0"),
        Column("draft_token", UUID(as_uuid=True)),
        timestamp("create_time"),
        timestamp("update_time"),
        Column("last_editor_id", ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False),
        timestamp("published_at", nullable=True, default=False),
        Column("publisher_id", ForeignKey("sys_user.id", ondelete="RESTRICT")),
        *fields,
        UniqueConstraint("product_id", "version"),
        Index(f"uq_{name}_active_product", "product_id", unique=True, postgresql_where=text("status = '1'")),
        CheckConstraint("version > 0"),
        CheckConstraint("status IN ('0', '1', '2')"),
        CheckConstraint(
            "(status = '0' AND draft_token IS NOT NULL AND published_at IS NULL AND publisher_id IS NULL)"
            " OR (status IN ('1', '2') AND draft_token IS NULL AND published_at IS NOT NULL"
            " AND publisher_id IS NOT NULL)"
        ),
    )


bom = version_table("basic_bom", Column("base_qty", Numeric(18, 4), nullable=False, server_default="1.0000"))
routing = version_table("basic_routing")

bom_item = entity(
    "basic_bom_item",
    Column("bom_id", ForeignKey(bom.c.id, ondelete="CASCADE"), nullable=False),
    Column("material_id", ForeignKey(material.c.id, ondelete="RESTRICT"), nullable=False, index=True),
    Column("qty", Numeric(18, 4), nullable=False),
    Column("sort_no", Integer, nullable=False),
    CheckConstraint("sort_no > 0"),
    Index("ix_basic_bom_item_order", "bom_id", "sort_no", "id"),
)

routing_step = entity(
    "basic_routing_step",
    Column("routing_id", ForeignKey(routing.c.id, ondelete="CASCADE"), nullable=False),
    Column("process_id", ForeignKey(process.c.id, ondelete="RESTRICT"), nullable=False, index=True),
    Column("seq", Integer, nullable=False),
    Column("remark", String(200)),
    Index("ix_basic_routing_step_order", "routing_id", "seq", "id"),
)

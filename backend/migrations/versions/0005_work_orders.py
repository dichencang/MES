"""Add work orders and permission nodes."""

from alembic import op
from sqlalchemy import delete, select

from app.models import system, workorder
from app.models.workorder_seed import permission_statements

revision = "0005_work_orders"
down_revision = "0004_plan_management"
branch_labels = None
depends_on = None

tables = (workorder.work_order, workorder.work_material, workorder.step,
          workorder.assignment, workorder.event)


def upgrade():
    bind = op.get_bind()
    workorder.numbers.create(bind)
    for table in tables:
        table.create(bind)
    for statement in permission_statements():
        op.execute(statement)


def downgrade():
    permission = system.permission
    condition = permission.c.permission_code.like("workorder:%")
    op.execute(delete(system.role_permission).where(
        system.role_permission.c.permission_id.in_(select(permission.c.id).where(condition)),
    ))
    op.execute(delete(permission).where(condition))
    bind = op.get_bind()
    for table in reversed(tables):
        table.drop(bind)
    workorder.numbers.drop(bind)

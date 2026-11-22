"""Create sales order and production plan tables."""

from alembic import op
from sqlalchemy import delete
from app.models import system
from app.models.plan_seed import permission_statements

from app.models import plan

revision = "0004_plan_management"
down_revision = "0003_basic_data"
branch_labels = None
depends_on = None

tables = (plan.sales_order, plan.sales_order_item, plan.production_plan)
sequences = (plan.order_numbers, plan.plan_numbers)


def upgrade():
    bind = op.get_bind()
    for sequence in sequences:
        sequence.create(bind)
    for table in tables:
        table.create(bind)
    for statement in permission_statements():
        op.execute(statement)


def downgrade():
    op.execute(delete(system.permission).where(system.permission.c.permission_code.like("plan:%")))
    bind = op.get_bind()
    for table in reversed(tables):
        table.drop(bind)
    for sequence in reversed(sequences):
        sequence.drop(bind)

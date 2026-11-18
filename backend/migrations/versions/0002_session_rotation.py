"""Record which sessions were revoked by refresh rotation."""

import sqlalchemy as sa
from alembic import op

revision = "0002_session_rotation"
down_revision = "0001_system"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sys_user_session",
        sa.Column("rotated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("sys_user_session", "rotated")

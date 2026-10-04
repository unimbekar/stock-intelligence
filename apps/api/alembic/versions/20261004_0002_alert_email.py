"""Alert email address and one-time notification flag."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261004_0002"
down_revision: str | None = "20261004_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("notify_email", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "alerts",
        sa.Column("notified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("alerts", "notified")
    op.drop_column("user_preferences", "notify_email")

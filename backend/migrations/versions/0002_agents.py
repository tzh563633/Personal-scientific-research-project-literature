"""Persist host Agent registration and assignment state."""
from alembic import op
import sqlalchemy as sa


revision = "0002_agents"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="offline"),
        sa.Column("capabilities", sa.JSON()),
        sa.Column("last_seen_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agents_name", "agents", ["name"], unique=True)
    op.create_index("ix_agents_status", "agents", ["status"], unique=False)
    op.add_column("agent_jobs", sa.Column("agent_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_agent_jobs_agent_id",
        "agent_jobs",
        "agents",
        ["agent_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_jobs_agent_id", "agent_jobs", type_="foreignkey")
    op.drop_column("agent_jobs", "agent_id")
    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_name", table_name="agents")
    op.drop_table("agents")

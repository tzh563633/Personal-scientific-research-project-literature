"""Add research asset library tables."""
from alembic import op
import sqlalchemy as sa


revision = "0007_research_assets"
down_revision = "0006_review_excel_inputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_methods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("use_cases", sa.Text(), nullable=True),
        sa.Column("steps", sa.Text(), nullable=True),
        sa.Column("advantages", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("related_project_id", sa.Integer(), sa.ForeignKey("code_projects.id"), nullable=True),
        sa.Column("related_paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "research_tools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("installation", sa.Text(), nullable=True),
        sa.Column("usage", sa.Text(), nullable=True),
        sa.Column("cautions", sa.Text(), nullable=True),
        sa.Column("related_project_id", sa.Integer(), sa.ForeignKey("code_projects.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "research_workflows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("research_workflows")
    op.drop_table("research_tools")
    op.drop_table("research_methods")

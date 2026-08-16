"""Store selected Excel inputs and review audit summaries."""
from alembic import op
import sqlalchemy as sa


revision = "0006_review_excel_inputs"
down_revision = "0005_folder_scan_install"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_frameworks", sa.Column("excel_path", sa.Text(), nullable=True))
    op.add_column(
        "review_outputs",
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "review_outputs",
        sa.Column("verified_source_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "review_outputs",
        sa.Column("full_text_source_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("review_outputs", sa.Column("fact_check_summary", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("review_outputs", "fact_check_summary")
    op.drop_column("review_outputs", "full_text_source_count")
    op.drop_column("review_outputs", "verified_source_count")
    op.drop_column("review_outputs", "source_count")
    op.drop_column("review_frameworks", "excel_path")

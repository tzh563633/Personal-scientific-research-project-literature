"""Store upload metadata and auditable review source records."""
from alembic import op
import sqlalchemy as sa


revision = "0003_files_review_sources"
down_revision = "0002_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_files", sa.Column("original_name", sa.Text(), nullable=True))
    op.add_column("paper_files", sa.Column("extension", sa.String(20), nullable=True))
    op.add_column("paper_files", sa.Column("mime_type", sa.String(120), nullable=True))
    op.create_table(
        "review_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "output_id",
            sa.Integer(),
            sa.ForeignKey("review_outputs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("doi", sa.String(255)),
        sa.Column("url", sa.Text()),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("full_text_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_review_sources_output_id", "review_sources", ["output_id"])
    op.create_index("ix_review_sources_doi", "review_sources", ["doi"])


def downgrade() -> None:
    op.drop_index("ix_review_sources_doi", table_name="review_sources")
    op.drop_index("ix_review_sources_output_id", table_name="review_sources")
    op.drop_table("review_sources")
    op.drop_column("paper_files", "mime_type")
    op.drop_column("paper_files", "extension")
    op.drop_column("paper_files", "original_name")

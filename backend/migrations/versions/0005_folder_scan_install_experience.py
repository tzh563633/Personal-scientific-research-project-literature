"""Add folder scan workflow metadata."""
from alembic import op
import sqlalchemy as sa


revision = "0005_folder_scan_install"
down_revision = "0004_revoked_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("excel_updates", sa.Column("paper_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "excel_updates",
        sa.Column("preserved_manual_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("journals", sa.Column("last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("journals", sa.Column("last_success_at", sa.DateTime(), nullable=True))
    op.add_column("journals", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("journals", sa.Column("last_item_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_jobs", sa.Column("job_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_agent_jobs_job_id", "agent_jobs", "jobs", ["job_id"], ["id"])
    op.create_table(
        "paper_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("recursive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_scan_at", sa.DateTime(), nullable=True),
        sa.Column("last_scan_job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "folder_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "folder_id",
            sa.Integer(),
            sa.ForeignKey("paper_folders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("modified_at", sa.DateTime(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=True),
        sa.Column("parse_job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("import_status", sa.String(20), nullable=False, server_default="discovered"),
        sa.Column("parse_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_folder_documents_folder_path", "folder_documents", ["folder_id", "relative_path"], unique=True)
    op.create_index("ix_folder_documents_sha256", "folder_documents", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_folder_documents_sha256", table_name="folder_documents")
    op.drop_index("ix_folder_documents_folder_path", table_name="folder_documents")
    op.drop_table("folder_documents")
    op.drop_table("paper_folders")
    op.drop_constraint("fk_agent_jobs_job_id", "agent_jobs", type_="foreignkey")
    op.drop_column("agent_jobs", "job_id")
    op.drop_column("journals", "last_item_count")
    op.drop_column("journals", "last_error")
    op.drop_column("journals", "last_success_at")
    op.drop_column("journals", "last_checked_at")
    op.drop_column("excel_updates", "preserved_manual_count")
    op.drop_column("excel_updates", "paper_count")

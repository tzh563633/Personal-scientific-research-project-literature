"""Initial research platform schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("doi", sa.String(255), unique=True),
        sa.Column("abstract", sa.Text()),
        sa.Column("core_topics", sa.Text()),
        sa.Column("secondary_topics", sa.Text()),
        sa.Column("innovation_points", sa.Text()),
        sa.Column("citation_gbt", sa.Text()),
        sa.Column("file_path", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("extra_metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "paper_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "paper_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("doi", sa.String(255)),
        sa.Column("matched_paper_id", sa.Integer(), sa.ForeignKey("papers.id")),
        sa.Column("citation_order", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "citation_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("in_text_marker", sa.String(50), nullable=False),
        sa.Column("reference_id", sa.Integer(), sa.ForeignKey("paper_references.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text()),
        sa.Column("result", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
    )
    op.create_table(
        "excel_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("added_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "manual_edits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(80), nullable=False),
        sa.Column("original_value", sa.Text()),
        sa.Column("edited_value", sa.Text()),
        sa.Column("edited_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "journals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("rss_url", sa.Text()),
        sa.Column("language", sa.String(10)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("journals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("exclude_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "journal_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("journals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.Text()),
        sa.Column("abstract", sa.Text()),
        sa.Column("url", sa.Text()),
        sa.Column("doi", sa.String(255)),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("journals.id")),
        sa.Column("journal_item_id", sa.Integer(), sa.ForeignKey("journal_items.id")),
        sa.Column("paper_title", sa.Text(), nullable=False),
        sa.Column("paper_url", sa.Text()),
        sa.Column("matched_keywords", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id")),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "code_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("git_repo_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(50)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
    )
    op.create_table(
        "agent_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("command_id", sa.Integer(), sa.ForeignKey("commands.id")),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON()),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("claimed_at", sa.DateTime()),
    )
    op.create_table(
        "review_frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "review_outputs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("review_frameworks.id")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("missing_pdf_md_path", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "academic_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("encrypted_config", sa.Text()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("detail", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "system_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.Text()),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "system_configs",
        "audit_logs",
        "academic_sources",
        "review_outputs",
        "review_frameworks",
        "agent_jobs",
        "commands",
        "code_projects",
        "notifications",
        "alerts",
        "journal_items",
        "keywords",
        "journals",
        "manual_edits",
        "excel_updates",
        "jobs",
        "citation_links",
        "paper_references",
        "paper_files",
        "papers",
        "users",
    ]:
        op.drop_table(table)

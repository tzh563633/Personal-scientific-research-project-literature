"""Add server-side JWT revocation records."""
from alembic import op
import sqlalchemy as sa


revision = "0004_revoked_tokens"
down_revision = "0003_files_review_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_revoked_tokens_token_hash", "revoked_tokens", ["token_hash"], unique=True)
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_token_hash", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")

"""Initial schema migration: users and prediction_records.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-11-16
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("consent_given", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("consent_terms_version", sa.String(length=32), nullable=True),
        sa.Column("consent_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_revoked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. Create prediction_records table
    op.create_table(
        "prediction_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("anonymized_input_hash", sa.String(length=64), nullable=False),
        sa.Column("estimated_probability", sa.Float(), nullable=False),
        sa.Column("binary_classification", sa.Integer(), nullable=False),
        sa.Column("operating_threshold", sa.Float(), server_default=sa.text("0.09"), nullable=False),
        sa.Column("model_version", sa.String(length=32), server_default="2.1.0", nullable=False),
        sa.Column("user_consent_given", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_records_id", "prediction_records", ["id"], unique=False)
    op.create_index("ix_prediction_records_user_id", "prediction_records", ["user_id"], unique=False)
    op.create_index("ix_prediction_records_anonymized_input_hash", "prediction_records", ["anonymized_input_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_prediction_records_anonymized_input_hash", table_name="prediction_records")
    op.drop_index("ix_prediction_records_user_id", table_name="prediction_records")
    op.drop_index("ix_prediction_records_id", table_name="prediction_records")
    op.drop_table("prediction_records")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

"""initial schema

Revision ID: 20260627_0001
Revises:
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260627_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_product_id", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("slug", sa.String(length=256), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("category", sa.String(length=256), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "source_product_id", name="uq_products_source_product"),
    )
    op.create_index("ix_products_url", "products", ["url"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("source_variant_id", sa.String(length=128), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("product_id", "source_variant_id", name="uq_variants_product_source"),
    )

    op.create_table(
        "product_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column(
            "variant_id",
            sa.String(length=36),
            sa.ForeignKey("product_variants.id"),
            nullable=True,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("availability", sa.String(length=32), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("quantity_limit", sa.Integer(), nullable=True),
        sa.Column("raw_state", sa.JSON(), nullable=False),
        sa.Column("collector_version", sa.String(length=64), nullable=False),
        sa.Column("fetch_status", sa.String(length=32), nullable=False),
        sa.Column("fetch_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_product_snapshots_product_observed", "product_snapshots", ["product_id", "observed_at"]
    )

    op.create_table(
        "scheduler_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scheduler_runs")
    op.drop_index("ix_product_snapshots_product_observed", table_name="product_snapshots")
    op.drop_table("product_snapshots")
    op.drop_table("product_variants")
    op.drop_index("ix_products_url", table_name="products")
    op.drop_table("products")

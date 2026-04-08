"""add_re_loans_table

Revision ID: c56f6c6372a0
Revises: efe3898fdf4b
Create Date: 2026-04-08 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c56f6c6372a0"
down_revision = "efe3898fdf4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "re_loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_number", sa.String(length=50), nullable=False),
        sa.Column("borrower_name", sa.String(length=255), nullable=True),
        sa.Column("sales_team_id", sa.Integer(), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("upb", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("original_balance", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("interest_rate", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("wam_months", sa.Integer(), nullable=True),
        sa.Column("ltv", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("dscr", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("property_type", sa.String(length=50), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("msa", sa.String(length=100), nullable=True),
        sa.Column("risk_rating", sa.String(length=10), nullable=True),
        sa.Column("prior_risk_rating", sa.String(length=10), nullable=True),
        sa.Column("rate_type", sa.String(length=20), nullable=True),
        sa.Column("origination_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("days_past_due", sa.Integer(), nullable=True),
        sa.Column("delinquency_status", sa.String(length=20), nullable=True),
        sa.Column("pipeline_stage", sa.String(length=30), nullable=True),
        sa.Column("vintage_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sales_team_id"], ["sales_teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_re_loans_id"), "re_loans", ["id"], unique=False)
    op.create_index(op.f("ix_re_loans_loan_number"), "re_loans", ["loan_number"], unique=False)
    op.create_index(op.f("ix_re_loans_as_of_date"), "re_loans", ["as_of_date"], unique=False)
    op.create_index(op.f("ix_re_loans_property_type"), "re_loans", ["property_type"], unique=False)
    op.create_index(op.f("ix_re_loans_state"), "re_loans", ["state"], unique=False)
    op.create_index(op.f("ix_re_loans_sales_team_id"), "re_loans", ["sales_team_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_re_loans_sales_team_id"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_state"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_property_type"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_as_of_date"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_loan_number"), table_name="re_loans")
    op.drop_index(op.f("ix_re_loans_id"), table_name="re_loans")
    op.drop_table("re_loans")

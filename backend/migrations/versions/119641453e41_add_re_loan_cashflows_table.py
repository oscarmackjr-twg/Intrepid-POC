"""add_re_loan_cashflows_table

Revision ID: 119641453e41
Revises: c56f6c6372a0
Create Date: 2026-04-08 00:00:01.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "119641453e41"
down_revision = "c56f6c6372a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "re_loan_cashflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("period_date", sa.Date(), nullable=False),
        sa.Column("scheduled_principal", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("actual_principal", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("scheduled_interest", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("actual_interest", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("noi", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["loan_id"], ["re_loans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_re_loan_cashflows_id"), "re_loan_cashflows", ["id"], unique=False)
    op.create_index(
        op.f("ix_re_loan_cashflows_loan_id_period_date"),
        "re_loan_cashflows",
        ["loan_id", "period_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_re_loan_cashflows_loan_id_period_date"), table_name="re_loan_cashflows")
    op.drop_index(op.f("ix_re_loan_cashflows_id"), table_name="re_loan_cashflows")
    op.drop_table("re_loan_cashflows")

"""Add standalone homework assignments."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0005_homeworks"
down_revision = "0004_roadmaps"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "homeworks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("teacher_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("tasks", JSONB(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("grade BETWEEN 1 AND 11", name="ck_homeworks_grade"),
        sa.CheckConstraint(
            "subject IN ('math', 'algebra', 'physics', 'geometry')",
            name="ck_homeworks_subject",
        ),
    )
    op.create_index("ix_homeworks_teacher_id", "homeworks", ["teacher_id"])


def downgrade():
    op.drop_index("ix_homeworks_teacher_id", table_name="homeworks")
    op.drop_table("homeworks")

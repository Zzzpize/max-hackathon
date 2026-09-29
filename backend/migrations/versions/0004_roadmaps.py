from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0004_roadmaps"
down_revision = "0003_teacher_states"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("teacher_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "grade BETWEEN 1 AND 11", name="ck_roadmaps_grade"
        ),
        sa.CheckConstraint(
            "subject IN ('math', 'algebra', 'physics', 'geometry')",
            name="ck_roadmaps_subject",
        ),
    )
    op.create_index("ix_roadmaps_teacher_id", "roadmaps", ["teacher_id"])


def downgrade():
    op.drop_index("ix_roadmaps_teacher_id", table_name="roadmaps")
    op.drop_table("roadmaps")

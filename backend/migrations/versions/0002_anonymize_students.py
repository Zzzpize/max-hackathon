"""Move student names from PostgreSQL into teacher-owned files."""

from alembic import op
import sqlalchemy as sa

from app.student_names import name_hash, save_name, get_name

revision = "0002_anonymize_students"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    students = sa.table(
        "students", sa.column("id", sa.String), sa.column("teacher_id", sa.String),
        sa.column("display_name", sa.String),
    )
    for student_id, teacher_id, name in connection.execute(
        sa.select(students.c.id, students.c.teacher_id, students.c.display_name)
    ):
        if name.startswith("sha256:"):
            continue
        save_name(teacher_id, student_id, name)
        connection.execute(
            students.update().where(students.c.id == student_id).values(
                display_name=name_hash(student_id, name)
            )
        )


def downgrade():
    connection = op.get_bind()
    students = sa.table(
        "students", sa.column("id", sa.String), sa.column("teacher_id", sa.String),
        sa.column("display_name", sa.String),
    )
    for student_id, teacher_id, stored in connection.execute(
        sa.select(students.c.id, students.c.teacher_id, students.c.display_name)
    ):
        if stored.startswith("sha256:"):
            connection.execute(students.update().where(students.c.id == student_id).values(
                display_name=get_name(teacher_id, student_id, stored)
            ))
            save_name(teacher_id, student_id, None)

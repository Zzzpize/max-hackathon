import importlib

from sqlalchemy import Column, MetaData, String, Table, create_engine, select

from app.config import settings
from app.student_names import get_name


def test_migration_moves_names_out_of_database(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    migration = importlib.import_module("migrations.versions.0002_anonymize_students")
    engine = create_engine("sqlite://")
    students = Table(
        "students", MetaData(), Column("id", String, primary_key=True),
        Column("teacher_id", String), Column("display_name", String),
    )
    students.create(engine)
    with engine.begin() as connection:
        connection.execute(students.insert().values(
            id="student-1", teacher_id="teacher-1", display_name="Иванов П."
        ))
        monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
        migration.upgrade()
        stored = connection.scalar(select(students.c.display_name))

    assert stored.startswith("sha256:")
    assert "Иванов" not in stored
    assert get_name("teacher-1", "student-1", stored) == "Иванов П."

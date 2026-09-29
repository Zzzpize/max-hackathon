import importlib

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.config import Config
from pathlib import Path
from sqlalchemy import create_engine, inspect


def test_homework_migration_upgrade_and_downgrade(monkeypatch):
    migration = importlib.import_module("migrations.versions.0005_homeworks")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    assert ScriptDirectory.from_config(config).get_current_head() == "0005_homeworks"
    assert migration.down_revision == "0004_roadmaps"

    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
            migration.upgrade()
            inspector = inspect(connection)
            columns = {column["name"]: column for column in inspector.get_columns("homeworks")}
            assert not columns["teacher_id"]["nullable"]
            assert columns["notes"]["nullable"]
            assert inspector.get_foreign_keys("homeworks") == []
            assert inspector.get_indexes("homeworks")[0]["column_names"] == ["teacher_id"]
            migration.downgrade()
            assert "homeworks" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()

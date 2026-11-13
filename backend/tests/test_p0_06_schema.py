from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.db.base import Base

BACKEND = Path(__file__).resolve().parents[1]


def test_alembic_initialized():
    assert (BACKEND / "alembic.ini").is_file()
    assert (BACKEND / "alembic" / "env.py").is_file()
    versions = BACKEND / "alembic" / "versions"
    assert versions.is_dir()
    assert any(versions.glob("*.py")), "expected at least one migration version"


def test_core_models_have_tenant_columns():
    # import models to register metadata
    from app.models import core  # noqa: F401

    tables = Base.metadata.tables
    for name in ["gyms", "branches", "users", "roles"]:
        assert name in tables, f"missing table: {name}"
    # every core table must have gym_id and branch_id columns
    for name in ["gyms", "branches", "users", "roles"]:
        cols = set(tables[name].columns.keys())
        assert "gym_id" in cols, f"{name} missing gym_id"
        assert "branch_id" in cols, f"{name} missing branch_id"


def test_migration_applies_cleanly_to_fresh_db(tmp_path):
    # apply migrations to a fresh sqlite db using alembic command API
    from alembic.config import Config

    from alembic import command

    db_path = tmp_path / "test.db"
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    insp = inspect(engine)
    assert set(["gyms", "branches", "users", "roles"]).issubset(set(insp.get_table_names()))
    for name in ["gyms", "branches", "users", "roles"]:
        cols = {c["name"] for c in insp.get_columns(name)}
        assert "gym_id" in cols and "branch_id" in cols

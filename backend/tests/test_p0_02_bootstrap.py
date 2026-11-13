from pathlib import Path
import importlib


BACKEND = Path(__file__).resolve().parents[1]


def test_pyproject_has_required_dependencies():
    pyproject = (BACKEND / "pyproject.toml").read_text(encoding="utf-8").lower()
    for dep in ["fastapi", "sqlalchemy", "alembic", "pydantic", "pytest"]:
        assert dep in pyproject, f"missing dependency mention: {dep}"
    # lint/type tools baseline
    assert ("ruff" in pyproject) or ("flake8" in pyproject) or ("black" in pyproject)
    assert ("mypy" in pyproject) or ("pyright" in pyproject)


def test_main_exposes_health_endpoint():
    mod = importlib.import_module("app.main")
    app = getattr(mod, "app")
    # use TestClient from fastapi
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"

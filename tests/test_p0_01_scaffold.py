from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_directories_exist():
    for name in ["backend", "frontend", "infra", "docs"]:
        assert (ROOT / name).is_dir(), f"missing directory: {name}"


def test_required_files_exist():
    for name in [".gitignore", "README.md"]:
        assert (ROOT / name).is_file(), f"missing file: {name}"


def test_readme_describes_stack_and_how_to_run():
    content = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    # stack mentions
    assert "fastapi" in content
    assert "react" in content
    assert "postgres" in content
    # how to run locally
    assert "docker compose" in content or "docker-compose" in content
    assert "run" in content or "setup" in content or "getting started" in content

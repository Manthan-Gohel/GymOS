from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_exists_and_runs_checks():
    wf = ROOT / ".github" / "workflows" / "ci.yml"
    assert wf.is_file(), "missing .github/workflows/ci.yml"
    content = wf.read_text(encoding="utf-8").lower()
    assert "push" in content and "pull_request" in content
    assert "pytest" in content
    assert "ruff" in content or "lint" in content
    assert "mypy" in content or "pyright" in content or "type" in content


def test_readme_documents_ci_status():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "ci" in readme or "github actions" in readme

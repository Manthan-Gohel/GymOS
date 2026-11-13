from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def test_lint_and_type_commands_documented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "ruff" in readme
    assert "mypy" in readme


def test_backend_ruff_baseline_passes():
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_backend_mypy_baseline_passes():
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "app"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

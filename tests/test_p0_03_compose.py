from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_defines_required_services():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ["api:", "db:", "redis:", "worker:"]:
        assert service in compose, f"missing service: {service}"
    assert "postgres" in compose.lower()


def test_env_example_exists_with_core_vars():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ["POSTGRES", "REDIS", "SECRET", "DATABASE_URL"]:
        assert key in env_example, f"missing env key hint: {key}"


def test_docs_include_compose_up_instructions():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "docker compose up" in readme or "docker-compose up" in readme

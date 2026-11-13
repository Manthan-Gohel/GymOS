import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_frontend_configs_exist():
    required_configs = [
        "package.json",
        "tsconfig.json",
        "tsconfig.node.json",
        "vite.config.ts",
        "tailwind.config.js",
        "postcss.config.js",
        "index.html",
        "playwright.config.ts",
    ]
    for cfg in required_configs:
        assert (FRONTEND / cfg).is_file(), f"missing frontend config file: {cfg}"


def test_package_json_has_required_dependencies():
    pkg_file = FRONTEND / "package.json"
    data = json.loads(pkg_file.read_text(encoding="utf-8"))

    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})

    # Core dependencies
    for d in ["react", "react-dom", "react-router-dom", "lucide-react"]:
        assert d in deps, f"missing dependency: {d}"

    # Dev / Build dependencies
    for d in ["vite", "typescript", "tailwindcss", "@playwright/test"]:
        assert d in dev_deps, f"missing devDependency: {d}"


def test_all_staff_panels_exist():
    panels = [
        "Login.tsx",
        "ReceptionPanel.tsx",
        "AdminPanel.tsx",
        "OwnerDashboard.tsx",
        "TrainerPanel.tsx",
    ]
    for panel in panels:
        path = FRONTEND / "src" / "pages" / panel
        assert path.is_file(), f"missing staff panel: {panel}"


def test_auth_shell_and_navigation_components_exist():
    components = [
        "components/Layout.tsx",
        "components/Navbar.tsx",
        "components/Sidebar.tsx",
        "components/ProtectedRoute.tsx",
        "context/AuthContext.tsx",
        "services/api.ts",
    ]
    for comp in components:
        path = FRONTEND / "src" / comp
        assert path.is_file(), f"missing component: {comp}"


def test_e2e_spec_exists():
    e2e_spec = FRONTEND / "tests" / "e2e" / "auth-and-panels.spec.ts"
    assert e2e_spec.is_file(), "missing e2e playwright test spec"
    content = e2e_spec.read_text(encoding="utf-8")
    assert "GymOS Staff Portal" in content

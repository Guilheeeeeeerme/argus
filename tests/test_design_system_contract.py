"""Design system wiring tests for the flattened monorepo."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
CONSUMERS = (
    ROOT / "apps/admin/package.json",
    ROOT / "apps/triage/package.json",
)
VITE_CONFIGS = (
    ROOT / "apps/admin/vite.config.ts",
    ROOT / "apps/triage/vite.config.ts",
)


def test_design_system_is_workspace_local_not_published() -> None:
    design_system = json.loads((ROOT / "packages/ui/package.json").read_text())
    assert design_system["name"] == "@argus/design-system"

    for package_path in CONSUMERS:
        package = json.loads(package_path.read_text())
        assert "@argus/design-system" not in package.get("dependencies", {})


def test_consumers_alias_the_design_system_and_shared_auth() -> None:
    for config_path in VITE_CONFIGS:
        text = config_path.read_text()
        assert "packages/ui/src" in text
        assert "@shared/auth" in text

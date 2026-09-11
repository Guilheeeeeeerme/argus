"""Root compose contract tests for the flattened monorepo."""

from pathlib import Path

import yaml

def _find_compose() -> Path:
    candidate = Path(__file__).resolve()
    for parent in candidate.parents:
        if (parent / "docker-compose.yml").is_file():
            return parent / "docker-compose.yml"
    raise FileNotFoundError("docker-compose.yml not found above test file")


COMPOSE = _find_compose()


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text())


def test_single_dmz_network() -> None:
    compose = _compose()
    assert compose["networks"]["argus_dmz"]["name"] == "argus_dmz"
    for service in (
        "postgres",
        "redis",
        "minio",
        "api",
        "prompt-eval",
        "admin",
        "triage",
        "stream-gateway",
        "stream-gateway-sync",
        "stream-prep",
    ):
        assert service in compose["services"], f"missing service: {service}"
        assert "argus_dmz" in compose["services"][service]["networks"]
    assert "worker" not in compose["services"]


def test_no_edge_tls_gateway() -> None:
    compose = _compose()
    names = " ".join(compose["services"])
    assert "caddy" not in names
    for service in compose["services"].values():
        ports = service.get("ports") or []
        assert not any("443" in str(p) for p in ports)


def test_hot_reload_bind_mounts() -> None:
    compose = _compose()
    assert "./apps/api:/app" in compose["services"]["api"]["volumes"]
    assert "./apps/admin:/app" in compose["services"]["admin"]["volumes"]
    assert "./apps/triage:/app" in compose["services"]["triage"]["volumes"]
    assert "--reload" in compose["services"]["api"]["command"]


def test_rabbitmq_is_gone() -> None:
    compose = _compose()
    assert "rabbitmq" not in compose["services"]

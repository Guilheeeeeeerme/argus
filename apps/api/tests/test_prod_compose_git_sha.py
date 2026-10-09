"""Prod compose must not override baked GIT_SHA with the moving IMAGE_TAG."""

from pathlib import Path


def test_prod_compose_does_not_bind_git_sha_to_image_tag() -> None:
    compose = (
        Path(__file__).resolve().parents[3] / "deploy" / "compose.prod.yml"
    ).read_text(encoding="utf-8")
    assert "GIT_SHA: ${IMAGE_TAG" not in compose
    assert "GIT_SHA: ${IMAGE_TAG:-unknown}" not in compose

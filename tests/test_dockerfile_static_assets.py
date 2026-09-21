from pathlib import Path


def test_docker_image_includes_download_templates() -> None:
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "COPY docs/templates ./docs/templates" in dockerfile

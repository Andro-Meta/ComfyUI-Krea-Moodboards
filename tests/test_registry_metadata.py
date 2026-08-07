from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_has_comfy_registry_metadata() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "comfyui-krea-moodboards"
    assert pyproject["project"]["version"] == "0.2.2"
    assert pyproject["project"]["dependencies"] == []
    assert pyproject["tool"]["comfy"]["PublisherId"] == "andrometa"
    assert pyproject["tool"]["comfy"]["DisplayName"] == "Krea Moodboards"
    assert "data" in pyproject["tool"]["comfy"]["includes"]
    assert "examples" in pyproject["tool"]["comfy"]["includes"]
    assert "web" in pyproject["tool"]["comfy"]["includes"]

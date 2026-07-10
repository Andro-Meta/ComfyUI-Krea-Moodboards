from __future__ import annotations

import json
from pathlib import Path

from moodboard_catalog import CATALOG_PATH, load_catalog


def test_bundled_catalog_contains_prompt_only_krea_moodboards() -> None:
    catalog = load_catalog(CATALOG_PATH)
    krea = [board for board in catalog if board.get("collection") == "krea"]
    andrometa = [board for board in catalog if board.get("collection") == "andrometa"]

    assert len(krea) == 3549
    assert len(andrometa) == 60
    assert all(board.get("url", "").startswith("https://www.krea.ai/moodboard-feed/") for board in krea)
    assert all("image_urls" not in board for board in catalog)
    assert all(board.get("primary_image_url", "").startswith("https://optim-images.krea.ai/") for board in krea)
    assert all(board.get("qwen_guidance", {}).get("prompt_guidance") for board in catalog)


def test_example_workflows_are_valid_json() -> None:
    example_paths = sorted(Path("examples").glob("*.json"))

    assert example_paths
    for path in example_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("nodes"), path
        assert payload.get("version"), path
        if payload.get("links"):
            assert payload.get("last_link_id") == max(link[0] for link in payload["links"]), path

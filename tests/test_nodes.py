from __future__ import annotations

import json

import nodes


def test_node_mappings_are_registered() -> None:
    import __init__ as package

    assert "KreaMoodboardSearch" in package.NODE_CLASS_MAPPINGS
    assert "KreaMoodboardApply" in package.NODE_CLASS_MAPPINGS
    assert package.NODE_DISPLAY_NAME_MAPPINGS["KreaMoodboardApply"] == "Krea Moodboard Apply"


def test_search_node_outputs_prompt_metadata_and_preview(monkeypatch) -> None:
    board = {
        "url": "https://www.krea.ai/moodboard-feed/example",
        "slug": "example",
        "uuid": "abc",
        "title": "Gothic Teal",
        "taste_profile": "Deep teal gothic style.",
        "keywords": ["gothic", "teal"],
        "qwen_guidance": {
            "prompt_guidance": "Use deep teal gothic lighting.",
            "negative_guidance": "Avoid flat daylight.",
            "style_axes": ["deep teal"],
            "conditioning_notes": [],
            "source_summary": "summary",
        },
    }
    monkeypatch.setattr(nodes, "_catalog", lambda: [board])

    positive, negative, title, metadata_json, preview = nodes.KreaMoodboardSearch().search(
        query="dark teal",
        top_k=5,
        min_score=1,
        random_from_top_k=0,
        seed=1,
        strength="normal",
    )

    assert title == "Gothic Teal"
    assert "Apply this Krea moodboard style" in positive
    assert negative == "Avoid flat daylight."
    assert json.loads(metadata_json)["url"] == board["url"]
    assert "Gothic Teal" in preview


def test_apply_node_combines_prompt_and_style_metadata() -> None:
    style = {
        "positive": "Apply this Krea moodboard style: warm pastel lighting.",
        "negative": "Avoid harsh contrast.",
        "title": "Warm Pastel",
        "metadata_json": json.dumps({"title": "Warm Pastel"}),
    }

    positive, negative, metadata_json = nodes.KreaMoodboardApply().apply(
        prompt="a glass teapot",
        negative_prompt="low quality",
        moodboard_positive=style["positive"],
        moodboard_negative=style["negative"],
        metadata_json=style["metadata_json"],
        strength="normal",
        style_only=False,
        separator="newline",
    )

    assert positive.startswith("a glass teapot")
    assert "warm pastel lighting" in positive
    assert negative == "low quality, Avoid harsh contrast."
    assert json.loads(metadata_json)["title"] == "Warm Pastel"

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


def test_mashup_node_accepts_metadata_json_and_outputs_preview(monkeypatch) -> None:
    boards = [
        {
            "url": "https://www.krea.ai/moodboard-feed/gothic",
            "slug": "gothic",
            "uuid": "gothic-uuid",
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
        },
        {
            "url": "https://www.krea.ai/moodboard-feed/pastel",
            "slug": "pastel",
            "uuid": "pastel-uuid",
            "title": "Pastel Product",
            "taste_profile": "Warm product studio style.",
            "keywords": ["pastel", "product"],
            "qwen_guidance": {
                "prompt_guidance": "Use warm pastel studio lighting.",
                "negative_guidance": "Avoid harsh contrast.",
                "style_axes": ["warm pastel"],
                "conditioning_notes": [],
                "source_summary": "summary",
            },
        },
    ]
    monkeypatch.setattr(nodes, "_catalog", lambda: boards)

    positive, negative, title, metadata_json, preview = nodes.KreaMoodboardMashup().mashup(
        board_1=json.dumps({"uuid": "gothic-uuid"}),
        board_2="pastel product",
        weight_1=0.7,
        weight_2=0.3,
        strength="normal",
    )

    assert title == "Mashup: Gothic Teal + Pastel Product"
    assert "Gothic Teal" in positive
    assert "Pastel Product" in positive
    assert "Avoid flat daylight" in negative
    assert json.loads(metadata_json)["source_count"] == 2
    assert "Gothic Teal" in preview
    assert "Paste metadata_json" in preview

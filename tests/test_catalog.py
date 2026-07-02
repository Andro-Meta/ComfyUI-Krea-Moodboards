from __future__ import annotations

import json
from pathlib import Path

import pytest

from moodboard_catalog import (
    CatalogLoadError,
    apply_style_to_prompt,
    catalog_listing,
    load_catalog,
    mashup_boards,
    random_board,
    resolve_board_reference,
    search_boards,
    style_from_board,
)


def write_catalog(path: Path) -> Path:
    payload = {
        "version": 1,
        "source": "fixture",
        "moodboards": [
            {
                "url": "https://www.krea.ai/moodboard-feed/abyssal-gothic-11111111-1111-5111-9111-111111111111",
                "slug": "abyssal-gothic-11111111-1111-5111-9111-111111111111",
                "uuid": "11111111-1111-5111-9111-111111111111",
                "title": "Abyssal Gothic",
                "taste_profile": "Deep teal gothic shadows and painterly dread.",
                "keywords": ["gothic romanticism", "deep teal", "chiaroscuro"],
                "primary_image_url": "https://optim-images.krea.ai/abyssal.webp",
                "qwen_guidance": {
                    "prompt_guidance": "Apply deep teal palette, gothic chiaroscuro, painterly texture, and solemn atmosphere.",
                    "negative_guidance": "Avoid flat bright daylight.",
                    "style_axes": ["deep teal", "gothic", "painterly"],
                    "conditioning_notes": ["Keep user subject primary."],
                    "source_summary": "Dark painterly gothic moodboard.",
                    "guidance_version": 1,
                },
            },
            {
                "url": "https://www.krea.ai/moodboard-feed/warm-product-pastel-22222222-2222-5222-9222-222222222222",
                "slug": "warm-product-pastel-22222222-2222-5222-9222-222222222222",
                "uuid": "22222222-2222-5222-9222-222222222222",
                "title": "Warm Product Pastel",
                "taste_profile": "Soft product photography with luminous pastel surfaces.",
                "keywords": ["product photo", "warm pastel", "minimal"],
                "primary_image_url": "https://optim-images.krea.ai/pastel.webp",
                "qwen_guidance": {
                    "prompt_guidance": "Use warm pastel product lighting, smooth surfaces, and restrained editorial composition.",
                    "negative_guidance": "Avoid harsh grunge contrast.",
                    "style_axes": ["warm pastel", "product", "minimal"],
                    "conditioning_notes": ["Use as art direction only."],
                    "source_summary": "Pastel product studio moodboard.",
                    "guidance_version": 1,
                },
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_catalog_preserves_source_urls_and_skips_image_fields(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    assert len(catalog) == 2
    assert catalog[0]["title"] == "Abyssal Gothic"
    assert catalog[0]["url"].startswith("https://www.krea.ai/moodboard-feed/")
    assert catalog[0]["primary_image_url"] == "https://optim-images.krea.ai/abyssal.webp"
    assert "image_urls" not in catalog[0]


def test_load_catalog_rejects_missing_catalog(tmp_path: Path) -> None:
    with pytest.raises(CatalogLoadError):
        load_catalog(tmp_path / "missing.json")


def test_search_weights_titles_keywords_and_synonyms(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    matches = search_boards(catalog, "dark teal photo", top_k=2)

    assert matches[0]["board"]["title"] == "Abyssal Gothic"
    assert matches[0]["score"] > matches[1]["score"]
    assert "deep teal" in matches[0]["matched_terms"]


def test_search_preview_includes_scores_keywords_and_urls(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    matches = search_boards(catalog, "warm product", top_k=1)

    assert "Warm Product Pastel" in matches[0]["preview"]
    assert "Score:" in matches[0]["preview"]
    assert "https://www.krea.ai/moodboard-feed/" in matches[0]["preview"]


def test_catalog_listing_outputs_titles_uuids_links_and_json(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    listing = catalog_listing(catalog, query="gothic", page=1, page_size=5)
    data = json.loads(listing["catalog_json"])

    assert "[Abyssal Gothic](https://www.krea.ai/moodboard-feed/abyssal-gothic" in listing["catalog_text"]
    assert "Copy into board_1-board_4: 11111111-1111-5111-9111-111111111111" in listing["catalog_text"]
    assert "UUID: 11111111-1111-5111-9111-111111111111" in listing["catalog_text"]
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Abyssal Gothic"
    assert data["items"][0]["uuid"] == "11111111-1111-5111-9111-111111111111"
    assert data["items"][0]["url"].startswith("https://www.krea.ai/moodboard-feed/")
    assert data["items"][0]["thumbnail_url"] == "https://optim-images.krea.ai/abyssal.webp"


def test_catalog_cards_include_thumbnail_and_selected_metadata(tmp_path: Path) -> None:
    from moodboard_catalog import catalog_cards

    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    cards = catalog_cards(catalog, query="warm", limit=5)

    assert cards["total"] == 1
    assert cards["items"][0]["title"] == "Warm Product Pastel"
    assert cards["items"][0]["thumbnail_url"] == "https://optim-images.krea.ai/pastel.webp"
    assert json.loads(cards["items"][0]["metadata_json"])["uuid"] == "22222222-2222-5222-9222-222222222222"


def test_catalog_cards_support_offset_paging(tmp_path: Path) -> None:
    from moodboard_catalog import catalog_cards

    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    first = catalog_cards(catalog, query="", limit=1, offset=0)
    second = catalog_cards(catalog, query="", limit=1, offset=1)

    assert first["total"] == 2
    assert first["items"][0]["uuid"] != second["items"][0]["uuid"]
    assert second["offset"] == 1


def test_catalog_cards_can_fetch_specific_uuids(tmp_path: Path) -> None:
    from moodboard_catalog import catalog_cards_by_uuid

    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    cards = catalog_cards_by_uuid(
        catalog,
        ["22222222-2222-5222-9222-222222222222", "missing", "11111111-1111-5111-9111-111111111111"],
    )

    assert cards["total"] == 2
    assert [item["uuid"] for item in cards["items"]] == [
        "22222222-2222-5222-9222-222222222222",
        "11111111-1111-5111-9111-111111111111",
    ]


def test_random_board_is_deterministic_and_can_use_top_matches(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    first = random_board(catalog, seed=42, query="product", random_from_top_k=2)
    second = random_board(catalog, seed=42, query="product", random_from_top_k=2)

    assert first["uuid"] == second["uuid"]


def test_balanced_random_does_not_let_photo_styles_dominate() -> None:
    photo_boards = [
        {
            "url": f"https://www.krea.ai/moodboard-feed/photo-{index}",
            "slug": f"photo-{index}",
            "uuid": f"photo-{index}",
            "title": f"Photo Style {index}",
            "taste_profile": "cinematic photo lens documentary film look",
            "keywords": ["photo", "cinematic"],
            "qwen_guidance": {
                "prompt_guidance": "Use photographic lens lighting and cinematic film texture.",
                "negative_guidance": "",
                "style_axes": ["photographic"],
                "conditioning_notes": [],
                "source_summary": "Photo style.",
            },
        }
        for index in range(20)
    ]
    illustration_board = {
        "url": "https://www.krea.ai/moodboard-feed/illustration",
        "slug": "illustration",
        "uuid": "illustration",
        "title": "Ink Illustration",
        "taste_profile": "flat ink drawing and illustrated poster language",
        "keywords": ["illustration", "ink"],
        "qwen_guidance": {
            "prompt_guidance": "Use ink illustration, flat shapes, and graphic poster texture.",
            "negative_guidance": "",
            "style_axes": ["illustration"],
            "conditioning_notes": [],
            "source_summary": "Illustration style.",
        },
    }
    catalog = photo_boards + [illustration_board]

    picks = [random_board(catalog, seed=seed, random_mode="balanced") for seed in range(100)]

    assert sum(board["uuid"] == "illustration" for board in picks) >= 25


def test_resolve_board_reference_accepts_metadata_json_or_search_text(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))
    metadata_ref = json.dumps({"uuid": "11111111-1111-5111-9111-111111111111"})

    from_metadata = resolve_board_reference(catalog, metadata_ref)
    from_search = resolve_board_reference(catalog, "warm product")

    assert from_metadata["title"] == "Abyssal Gothic"
    assert from_search["title"] == "Warm Product Pastel"


def test_style_from_board_returns_positive_negative_and_metadata(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    style = style_from_board(catalog[0], strength="normal")
    metadata = json.loads(style["metadata_json"])

    assert style["title"] == "Abyssal Gothic"
    assert "Apply this Krea moodboard style" in style["positive"]
    assert "Avoid flat bright daylight" in style["negative"]
    assert metadata["url"] == catalog[0]["url"]
    assert metadata["style_axes"] == ["deep teal", "gothic", "painterly"]


def test_apply_style_keeps_user_prompt_primary(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))
    style = style_from_board(catalog[0])

    applied = apply_style_to_prompt(
        "a ceramic fox on a table",
        "",
        style,
        separator="newline",
        style_only=False,
    )

    assert applied["positive"].startswith("a ceramic fox on a table")
    assert "Apply this Krea moodboard style" in applied["positive"]
    assert applied["negative"] == "Avoid flat bright daylight."


def test_mashup_dedupes_negative_guidance_and_style_axes(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path / "catalog.json"))

    mashup = mashup_boards([catalog[0], catalog[1]], weights=[0.7, 0.3])
    metadata = json.loads(mashup["metadata_json"])

    assert "Abyssal Gothic" in mashup["positive"]
    assert "Warm Product Pastel" in mashup["positive"]
    assert mashup["title"] == "Mashup: Abyssal Gothic + Warm Product Pastel"
    assert "Avoid flat bright daylight" in mashup["negative"]
    assert metadata["source_count"] == 2
    assert "deep teal" in metadata["style_axes"]
    assert "Abyssal Gothic" in mashup["preview"]
    assert "Warm Product Pastel" in mashup["preview"]

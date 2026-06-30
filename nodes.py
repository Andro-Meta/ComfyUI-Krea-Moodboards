from __future__ import annotations

import json
from functools import lru_cache

from moodboard_catalog import (
    CATALOG_PATH,
    apply_style_to_prompt,
    catalog_listing,
    find_board,
    load_catalog,
    mashup_boards,
    random_board,
    resolve_board_reference,
    search_boards,
    style_from_board,
)


STRENGTHS = ["concise", "normal", "strong"]
SEPARATORS = ["newline", "comma"]
RANDOM_MODES = ["balanced", "any", "non_photo", "photo"]


@lru_cache(maxsize=1)
def _catalog():
    return load_catalog(CATALOG_PATH)


class KreaMoodboardStyle:
    CATEGORY = "Krea/Moodboards"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "title", "metadata_json")
    FUNCTION = "style"
    DESCRIPTION = "Look up one Krea moodboard by title, slug, UUID, URL, or search text."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "title_slug_uuid_or_url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Enter a Krea moodboard title, slug, UUID, URL, or search phrase.",
                    },
                ),
                "strength": (
                    STRENGTHS,
                    {
                        "default": "normal",
                        "tooltip": "Controls how much moodboard detail is added to the prompt text.",
                    },
                ),
            }
        }

    def style(self, title_slug_uuid_or_url: str, strength: str):
        board = find_board(_catalog(), title_slug_uuid_or_url)
        style = style_from_board(board, strength=strength)
        return style["positive"], style["negative"], style["title"], style["metadata_json"]


class KreaMoodboardCatalogBrowser:
    CATEGORY = "Krea/Moodboards"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("catalog_text", "catalog_json")
    FUNCTION = "browse"
    DESCRIPTION = "List Krea moodboard names, UUIDs, keywords, and source URLs so users can identify exact catalog entries."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "query": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Optional search query. Leave blank to browse alphabetically.",
                    },
                ),
                "page": (
                    "INT",
                    {"default": 1, "min": 1, "max": 250, "step": 1, "tooltip": "Page number for browsing results."},
                ),
                "page_size": (
                    "INT",
                    {
                        "default": 25,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "tooltip": "How many moodboards to list in catalog_text.",
                    },
                ),
            }
        }

    def browse(self, query: str, page: int, page_size: int):
        listing = catalog_listing(_catalog(), query=query, page=page, page_size=page_size)
        return listing["catalog_text"], listing["catalog_json"]


class KreaMoodboardSearch:
    CATEGORY = "Krea/Moodboards"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "title", "metadata_json", "preview")
    FUNCTION = "search"
    DESCRIPTION = "Search 2500 Krea moodboard prompt styles by mood, color, medium, lighting, texture, or title."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "query": (
                    "STRING",
                    {
                        "default": "dark teal gothic",
                        "multiline": False,
                        "tooltip": "Search words like mood, color, lighting, medium, texture, or title fragments.",
                    },
                ),
                "top_k": (
                    "INT",
                    {"default": 5, "min": 1, "max": 25, "step": 1, "tooltip": "Number of matches to preview."},
                ),
                "min_score": (
                    "INT",
                    {"default": 1, "min": 0, "max": 500, "step": 1, "tooltip": "Minimum search score to accept."},
                ),
                "random_from_top_k": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 25,
                        "step": 1,
                        "tooltip": "0 uses the best match. Greater than 0 randomly picks from the top N matches.",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFF,
                        "step": 1,
                        "tooltip": "Seed for random_from_top_k.",
                    },
                ),
                "strength": (
                    STRENGTHS,
                    {"default": "normal", "tooltip": "Controls detail level in the positive style text."},
                ),
                "random_mode": (
                    RANDOM_MODES,
                    {
                        "default": "balanced",
                        "tooltip": "balanced samples style families first; any samples the whole pool; non_photo avoids photo-family boards.",
                    },
                ),
            }
        }

    def search(
        self,
        query: str,
        top_k: int,
        min_score: int,
        random_from_top_k: int,
        seed: int,
        strength: str,
        random_mode: str = "balanced",
    ):
        catalog = _catalog()
        matches = search_boards(catalog, query, top_k=top_k, min_score=min_score)
        if not matches:
            raise ValueError(f"No Krea moodboards matched query: {query}")
        if random_from_top_k > 0:
            board = random_board(
                catalog,
                seed=seed,
                query=query,
                random_from_top_k=min(random_from_top_k, top_k),
                min_score=min_score,
                random_mode=random_mode,
            )
        else:
            board = matches[0]["board"]
        style = style_from_board(board, strength=strength)
        preview = "\n".join(match["preview"] for match in matches)
        return style["positive"], style["negative"], style["title"], style["metadata_json"], preview


class KreaMoodboardRandom:
    CATEGORY = "Krea/Moodboards"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "title", "metadata_json")
    FUNCTION = "random_style"
    DESCRIPTION = "Pick a deterministic random Krea moodboard, optionally filtered by a search query."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF, "step": 1}),
                "query": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Optional search query used to narrow the random pool.",
                    },
                ),
                "random_from_top_k": (
                    "INT",
                    {"default": 25, "min": 1, "max": 100, "step": 1, "tooltip": "Random pool size after search."},
                ),
                "strength": (STRENGTHS, {"default": "normal"}),
                "random_mode": (
                    RANDOM_MODES,
                    {
                        "default": "balanced",
                        "tooltip": "balanced samples style families first so photo boards do not dominate random picks.",
                    },
                ),
            }
        }

    def random_style(
        self,
        seed: int,
        query: str,
        random_from_top_k: int,
        strength: str,
        random_mode: str = "balanced",
    ):
        board = random_board(
            _catalog(),
            seed=seed,
            query=query,
            random_from_top_k=random_from_top_k,
            random_mode=random_mode,
        )
        style = style_from_board(board, strength=strength)
        return style["positive"], style["negative"], style["title"], style["metadata_json"]


class KreaMoodboardMashup:
    CATEGORY = "Krea/Moodboards"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "title", "metadata_json", "preview")
    FUNCTION = "mashup"
    DESCRIPTION = "Blend two to four Krea moodboards into one prompt style."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "board_1": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Paste metadata_json from another Krea Moodboard node, or type a title, search phrase, UUID, slug, or URL.",
                    },
                ),
                "board_2": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Paste metadata_json from another Krea Moodboard node, or type a title, search phrase, UUID, slug, or URL.",
                    },
                ),
                "weight_1": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 5.0, "step": 0.05}),
                "weight_2": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 5.0, "step": 0.05}),
                "strength": (STRENGTHS, {"default": "normal"}),
            },
            "optional": {
                "board_3": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Optional third board: metadata_json, title, search phrase, UUID, slug, or URL.",
                    },
                ),
                "board_4": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Optional fourth board: metadata_json, title, search phrase, UUID, slug, or URL.",
                    },
                ),
                "weight_3": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 5.0, "step": 0.05}),
                "weight_4": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 5.0, "step": 0.05}),
            },
        }

    def mashup(
        self,
        board_1: str,
        board_2: str,
        weight_1: float,
        weight_2: float,
        strength: str,
        board_3: str = "",
        board_4: str = "",
        weight_3: float = 1.0,
        weight_4: float = 1.0,
    ):
        catalog = _catalog()
        names = [board_1, board_2, board_3, board_4]
        weights = [weight_1, weight_2, weight_3, weight_4]
        boards = [resolve_board_reference(catalog, name) for name in names if str(name or "").strip()]
        style = mashup_boards(boards, weights=weights[: len(boards)], strength=strength)
        return style["positive"], style["negative"], style["title"], style["metadata_json"], style["preview"]


class KreaMoodboardApply:
    CATEGORY = "Krea/Moodboards"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "metadata_json")
    FUNCTION = "apply"
    DESCRIPTION = "Append a moodboard style block to a user prompt before Krea 2 prompt enhancement or Qwen3-VL encoding."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Your main image prompt."}),
                "negative_prompt": (
                    "STRING",
                    {"default": "", "multiline": True, "tooltip": "Existing negative prompt, if your workflow uses one."},
                ),
                "moodboard_positive": (
                    "STRING",
                    {"default": "", "multiline": True, "tooltip": "Positive output from a Krea Moodboard node."},
                ),
                "moodboard_negative": (
                    "STRING",
                    {"default": "", "multiline": True, "tooltip": "Negative output from a Krea Moodboard node."},
                ),
                "metadata_json": (
                    "STRING",
                    {"default": "{}", "multiline": True, "tooltip": "Metadata JSON from a Krea Moodboard node."},
                ),
                "strength": (
                    STRENGTHS,
                    {"default": "normal", "tooltip": "Reserved for workflow clarity; source nodes apply the style strength."},
                ),
                "style_only": (
                    "BOOLEAN",
                    {"default": False, "tooltip": "Output only the moodboard style text, without the user prompt."},
                ),
                "separator": (
                    SEPARATORS,
                    {"default": "newline", "tooltip": "Join user prompt and style block with newlines or commas."},
                ),
            }
        }

    def apply(
        self,
        prompt: str,
        negative_prompt: str,
        moodboard_positive: str,
        moodboard_negative: str,
        metadata_json: str,
        strength: str,
        style_only: bool,
        separator: str,
    ):
        style = {
            "positive": moodboard_positive,
            "negative": moodboard_negative,
            "metadata_json": _valid_json(metadata_json),
        }
        applied = apply_style_to_prompt(prompt, negative_prompt, style, separator=separator, style_only=style_only)
        return applied["positive"], applied["negative"], applied["metadata_json"]


def _valid_json(value: str) -> str:
    try:
        json.loads(value or "{}")
    except json.JSONDecodeError:
        return "{}"
    return value or "{}"

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parent / "data" / "krea_moodboards_slim.json"


class CatalogLoadError(RuntimeError):
    """Raised when the bundled moodboard catalog cannot be loaded."""


SYNONYMS: dict[str, tuple[str, ...]] = {
    "photo": ("photoreal", "photographic", "photography", "cinematic", "documentary"),
    "photograph": ("photo", "photoreal", "photography", "cinematic", "documentary"),
    "dark": ("noir", "gothic", "low key", "shadow", "moody"),
    "bright": ("luminous", "high key", "glow", "radiant"),
    "anime": ("manga", "illustration", "illustrated"),
    "retro": ("vintage", "nostalgic", "throwback"),
    "product": ("studio", "editorial", "commercial"),
    "grainy": ("film grain", "analog", "documentary", "textured"),
}

FIELD_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("title", 24),
    ("keywords", 18),
    ("style_axes", 16),
    ("prompt_guidance", 12),
    ("taste_profile", 10),
    ("source_summary", 8),
    ("conditioning_notes", 6),
    ("negative_guidance", 3),
)


def load_catalog(path: str | Path = CATALOG_PATH) -> list[dict[str, Any]]:
    catalog_path = Path(path)
    if not catalog_path.exists():
        raise CatalogLoadError(f"Krea moodboard catalog not found: {catalog_path}")
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CatalogLoadError(f"Krea moodboard catalog is not valid JSON: {catalog_path}") from exc

    raw_items = payload.get("moodboards", payload if isinstance(payload, list) else [])
    if not isinstance(raw_items, list):
        raise CatalogLoadError("Krea moodboard catalog must contain a moodboards list.")

    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        guidance = item.get("qwen_guidance") if isinstance(item.get("qwen_guidance"), dict) else {}
        prompt_guidance = str(guidance.get("prompt_guidance") or "").strip()
        if not title or not prompt_guidance:
            continue
        cleaned = {
            "url": str(item.get("url") or "").strip(),
            "slug": str(item.get("slug") or "").strip(),
            "uuid": str(item.get("uuid") or "").strip(),
            "title": title,
            "taste_profile": str(item.get("taste_profile") or "").strip(),
            "keywords": _string_list(item.get("keywords")),
            "qwen_guidance": {
                "prompt_guidance": prompt_guidance,
                "negative_guidance": str(guidance.get("negative_guidance") or "").strip(),
                "style_axes": _string_list(guidance.get("style_axes")),
                "conditioning_notes": _string_list(guidance.get("conditioning_notes")),
                "source_summary": str(guidance.get("source_summary") or "").strip(),
                "guidance_version": int(guidance.get("guidance_version") or 1),
            },
        }
        items.append(cleaned)
    return items


def search_boards(
    catalog: list[dict[str, Any]],
    query: str,
    *,
    top_k: int = 5,
    min_score: int = 1,
) -> list[dict[str, Any]]:
    expanded_terms = _expand_query(query)
    if not expanded_terms:
        matches = [{"board": board, "score": 1, "matched_terms": [], "preview": ""} for board in catalog[:top_k]]
    else:
        matches = []
        for board in catalog:
            score, matched_terms = _score_board(board, expanded_terms)
            if score >= min_score:
                matches.append(
                    {
                        "board": board,
                        "score": score,
                        "matched_terms": matched_terms,
                        "preview": _preview(board, score, matched_terms),
                    }
                )
        matches.sort(key=lambda match: (-int(match["score"]), str(match["board"].get("title") or "")))
    return matches[: max(1, min(int(top_k or 5), 25))]


def random_board(
    catalog: list[dict[str, Any]],
    *,
    seed: int,
    query: str = "",
    random_from_top_k: int = 0,
    min_score: int = 1,
) -> dict[str, Any]:
    pool = catalog
    if query.strip():
        top_k = random_from_top_k if random_from_top_k > 0 else 25
        matches = search_boards(catalog, query, top_k=top_k, min_score=min_score)
        pool = [match["board"] for match in matches]
    if not pool:
        raise ValueError("No Krea moodboards matched the query.")
    return random.Random(int(seed)).choice(pool)


def find_board(catalog: list[dict[str, Any]], value: str) -> dict[str, Any]:
    needle = _normalize_spaces(value).lower()
    if not needle:
        raise ValueError("Provide a moodboard title, slug, uuid, or URL.")
    for board in catalog:
        candidates = [
            str(board.get("title") or ""),
            str(board.get("slug") or ""),
            str(board.get("uuid") or ""),
            str(board.get("url") or ""),
        ]
        if any(_normalize_spaces(candidate).lower() == needle for candidate in candidates):
            return board
    matches = search_boards(catalog, value, top_k=1, min_score=1)
    if matches:
        return matches[0]["board"]
    raise ValueError(f"No Krea moodboard matched: {value}")


def style_from_board(board: dict[str, Any], *, strength: str = "normal") -> dict[str, str]:
    guidance = _guidance(board)
    style_axes = _string_list(guidance.get("style_axes"))
    keywords = _string_list(board.get("keywords"))
    notes = _string_list(guidance.get("conditioning_notes"))
    title = str(board.get("title") or "Krea Moodboard").strip()
    prompt_guidance = _sentence(str(guidance.get("prompt_guidance") or ""))

    if strength == "concise":
        parts = [prompt_guidance]
    elif strength == "strong":
        parts = [
            f"{title}: {prompt_guidance}",
            str(board.get("taste_profile") or "").strip(),
            f"Keywords: {', '.join(keywords)}" if keywords else "",
            f"Style axes: {', '.join(style_axes)}" if style_axes else "",
            f"Notes: {', '.join(notes)}" if notes else "",
        ]
    else:
        parts = [
            f"{title}: {prompt_guidance}",
            f"Keywords: {', '.join(keywords)}" if keywords else "",
            f"Style axes: {', '.join(style_axes)}" if style_axes else "",
        ]
    positive = "Apply this Krea moodboard style: " + " ".join(part for part in parts if part).strip()
    negative = _sentence(str(guidance.get("negative_guidance") or ""))
    metadata = {
        "title": title,
        "uuid": str(board.get("uuid") or ""),
        "slug": str(board.get("slug") or ""),
        "url": str(board.get("url") or ""),
        "keywords": keywords,
        "style_axes": style_axes,
        "source_summary": str(guidance.get("source_summary") or ""),
    }
    return {
        "positive": _sentence(positive),
        "negative": negative,
        "title": title,
        "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
    }


def apply_style_to_prompt(
    prompt: str,
    negative_prompt: str,
    style: dict[str, str],
    *,
    separator: str = "newline",
    style_only: bool = False,
) -> dict[str, str]:
    moodboard_positive = str(style.get("positive") or "").strip()
    moodboard_negative = str(style.get("negative") or "").strip()
    base_prompt = str(prompt or "").strip()
    base_negative = str(negative_prompt or "").strip()
    sep = "\n\n" if separator == "newline" else ", "

    if style_only or not base_prompt:
        positive = moodboard_positive
    elif moodboard_positive:
        positive = f"{base_prompt}{sep}{moodboard_positive}"
    else:
        positive = base_prompt

    if base_negative and moodboard_negative:
        negative = f"{base_negative}, {moodboard_negative}"
    else:
        negative = base_negative or moodboard_negative

    return {
        "positive": positive,
        "negative": negative,
        "metadata_json": str(style.get("metadata_json") or "{}"),
    }


def mashup_boards(
    boards: list[dict[str, Any]],
    *,
    weights: list[float] | None = None,
    strength: str = "normal",
) -> dict[str, str]:
    if len(boards) < 2:
        raise ValueError("Choose at least two Krea moodboards for a mashup.")
    clean_weights = weights or [1.0] * len(boards)
    positives: list[str] = []
    negatives: list[str] = []
    style_axes: list[str] = []
    sources: list[dict[str, str]] = []

    for index, board in enumerate(boards[:4]):
        weight = float(clean_weights[index]) if index < len(clean_weights) else 1.0
        style = style_from_board(board, strength=strength)
        title = style["title"]
        positives.append(f"{title} (weight {weight:.2f}): {style['positive']}")
        if style["negative"]:
            negatives.append(style["negative"])
        metadata = json.loads(style["metadata_json"])
        for axis in metadata.get("style_axes", []):
            if axis and axis not in style_axes:
                style_axes.append(axis)
        sources.append({"title": title, "url": metadata.get("url", ""), "uuid": metadata.get("uuid", "")})

    metadata = {"source_count": len(sources), "sources": sources, "style_axes": style_axes}
    return {
        "positive": "Blend these Krea moodboard styles: " + " | ".join(positives),
        "negative": " ".join(_dedupe(negatives)),
        "title": "Krea Moodboard Mashup",
        "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
    }


def _score_board(board: dict[str, Any], expanded_terms: list[str]) -> tuple[int, list[str]]:
    score = 0
    matched: list[str] = []
    fields = _search_fields(board)
    for field, weight in FIELD_WEIGHTS:
        text = fields.get(field, "")
        text_low = text.lower()
        for term in expanded_terms:
            if term in text_low:
                score += weight * (2 if " " in term else 1)
                _append_match(matched, _best_match_label(board, field, term))
    return score, matched[:12]


def _search_fields(board: dict[str, Any]) -> dict[str, str]:
    guidance = _guidance(board)
    return {
        "title": str(board.get("title") or ""),
        "keywords": " ".join(_string_list(board.get("keywords"))),
        "taste_profile": str(board.get("taste_profile") or ""),
        "prompt_guidance": str(guidance.get("prompt_guidance") or ""),
        "negative_guidance": str(guidance.get("negative_guidance") or ""),
        "style_axes": " ".join(_string_list(guidance.get("style_axes"))),
        "conditioning_notes": " ".join(_string_list(guidance.get("conditioning_notes"))),
        "source_summary": str(guidance.get("source_summary") or ""),
    }


def _expand_query(query: str) -> list[str]:
    tokens = _tokens(query)
    terms: list[str] = []
    for token in tokens:
        for variant in _variants(token):
            _append_match(terms, variant)
        for synonym in SYNONYMS.get(token, ()):
            _append_match(terms, synonym)
            for synonym_token in _tokens(synonym):
                _append_match(terms, synonym_token)
    phrase = _normalize_spaces(query).lower()
    if " " in phrase:
        _append_match(terms, phrase)
    return terms


def _best_match_label(board: dict[str, Any], field: str, term: str) -> str:
    if field == "title":
        return str(board.get("title") or term)
    if field == "keywords":
        for keyword in _string_list(board.get("keywords")):
            if term in keyword.lower():
                return keyword
    if field == "style_axes":
        for axis in _string_list(_guidance(board).get("style_axes")):
            if term in axis.lower():
                return axis
    return term


def _preview(board: dict[str, Any], score: int, matched_terms: list[str]) -> str:
    keywords = ", ".join(_string_list(board.get("keywords"))[:6])
    terms = ", ".join(matched_terms[:8]) if matched_terms else "none"
    return (
        f"{board.get('title', 'Untitled')} | Score: {score} | "
        f"Keywords: {keywords or 'none'} | Matched: {terms} | URL: {board.get('url', '')}"
    )


def _guidance(board: dict[str, Any]) -> dict[str, Any]:
    guidance = board.get("qwen_guidance")
    return guidance if isinstance(guidance, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _variants(token: str) -> tuple[str, ...]:
    variants = {token}
    if token.endswith("s") and len(token) > 3:
        variants.add(token[:-1])
    else:
        variants.add(f"{token}s")
    return tuple(v for v in variants if v)


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _sentence(text: str) -> str:
    cleaned = _normalize_spaces(text)
    if not cleaned:
        return ""
    return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."


def _append_match(values: list[str], value: str) -> None:
    cleaned = _normalize_spaces(value).lower() if value == value.lower() else _normalize_spaces(value)
    if cleaned and cleaned not in values:
        values.append(cleaned)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _normalize_spaces(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out

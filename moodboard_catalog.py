from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parent / "data" / "krea_moodboards_slim.json"
ANDROMETA_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "andrometa_moodboards.json"
THUMB_CACHE_DIR = Path(__file__).resolve().parent / "data" / "thumb_cache"
THUMB_SIZE = 256


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

STYLE_FAMILY_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("anime", ("anime", "manga", "kawaii", "chibi", "retroanime")),
    ("illustration", ("illustration", "illustrated", "ink", "watercolor", "drawing", "sketch", "storybook")),
    ("graphic", ("graphic", "poster", "typography", "halftone", "pop art", "comic", "vector")),
    ("abstract", ("abstract", "abstraction", "geometric", "surreal", "spectral", "iridescent")),
    ("3d", ("3d", "voxel", "isometric", "clay", "render", "cgi", "plastic")),
    ("photo", ("photo", "photograph", "photographic", "photoreal", "documentary", "camera", "lens")),
    ("cinematic", ("cinematic", "film", "35mm", "noir", "editorial")),
)

# ---------------------------------------------------------------------------
# Subject-safety sanitization (mirrors the Krea 2 Studio moodboard pipeline).
# Moodboards must transfer style to arbitrary user subjects: guidance may never
# insert people/figures/objects, and negatives may never ban the user's subject
# or fight image quality.
# ---------------------------------------------------------------------------

STYLE_GUARDRAIL = (
    "Style-only Krea moodboard guidance: Apply the following only to the visual "
    "treatment of the subject and scene described above. Do not add, remove, "
    "replace, or change the requested subject matter. Do not introduce people, "
    "faces, figures, animals, vehicles, architecture, text, or objects unless "
    "they are explicitly requested in the main prompt."
)

SUBJECT_LOCK_TERMS: tuple[str, ...] = (
    "crowd", "crowds", "people", "person", "persons", "human", "humans",
    "figure", "figures", "man", "woman", "men", "women", "child", "children",
    "animal", "animals", "lettering", "building", "buildings",
    "architecture", "architectural", "vehicle", "vehicles", "face", "faces",
    "populated", "unpopulated", "empty scene", "empty scenes",
)

SUBJECT_STYLE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:a|an|the)\s+(?:black and white|high-contrast|glitchy|cinematic|close-up)?\s*portrait of\s+(?:a|an|the)?\s*[^.]+", re.I),
     "portrait-style framing for the requested subject"),
    (re.compile(r"\b(?:a|the)\s+lone figure\b", re.I), "a high-contrast silhouette treatment"),
    (re.compile(r"\b(?:lone|solitary|single|isolated)(?:,?\s+\w+){0,2}?\s+(?:silhouette|figure)s?\b", re.I),
     "high-contrast silhouette treatment"),
    (re.compile(r"\bcentered figure\b", re.I), "center-weighted contrast"),
    (re.compile(r"\bmany people\b", re.I), "multi-subject compositions"),
    (re.compile(r"\bno people\b", re.I), "subject-agnostic compositions"),
    (re.compile(r"\b(?:a|an|the)\s+(?:(?:single|lone|solitary|young|old|elderly)\s+){0,3}(?:woman|man|girl|boy|person|figure|child|face|subject|creature|animal)\b[^.]*", re.I),
     "the requested subject rendered with the board's palette, lighting, and texture"),
)

NEGATIVE_QUALITY_BAN_RE = re.compile(
    r"\b(?:photorealism|photorealistic|photo-realistic|realism|realistic|"
    r"sharp|sharpness|crisp|clarity|clear|high[- ]resolution|resolution|"
    r"detail|detailed|details|quality|anatomical|anatomy)\b",
    re.I,
)


def abstract_style_prose(text: str) -> str:
    """Rewrite concrete subject phrasing in style prose into rendering treatments."""
    result = str(text or "")
    for pattern, replacement in SUBJECT_STYLE_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    return result


def sanitize_style_fragment(text: str) -> str:
    """Sanitize a short keyword/axis; drop it entirely if a subject noun survives."""
    value = _normalize_spaces(abstract_style_prose(text))
    low = value.lower()
    if any(term in low for term in SUBJECT_LOCK_TERMS):
        return ""
    return value


def sanitize_style_prose(text: str) -> str:
    """Rewrite subject phrasing in prose; drop sentences that still leak subjects.

    Used for Krea taste profiles, which describe example images and may mention
    their subjects outright.
    """
    rewritten = abstract_style_prose(text)
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", _normalize_spaces(rewritten)):
        low = sentence.lower()
        if any(term in low for term in SUBJECT_LOCK_TERMS):
            continue
        if sentence:
            kept.append(sentence)
    return " ".join(kept)


def sanitize_negative_guidance(text: str) -> str:
    """Keep style-quality negative clauses; drop subject bans and quality bans."""
    clauses = re.split(r"(?<=[.;])\s+|,\s+and\s+|,\s+or\s+", str(text or ""))
    kept: list[str] = []
    for clause in clauses:
        low = clause.lower()
        if any(term in low for term in SUBJECT_LOCK_TERMS):
            continue
        if NEGATIVE_QUALITY_BAN_RE.search(clause):
            continue
        cleaned = clause.strip(" ,;.")
        if cleaned and cleaned not in kept:
            kept.append(cleaned)
    return ", ".join(kept)


def _load_catalog_file(catalog_path: Path, *, default_collection: str = "krea") -> list[dict[str, Any]]:
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
            "primary_image_url": str(item.get("primary_image_url") or "").strip(),
            "collection": str(item.get("collection") or default_collection).strip() or default_collection,
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


def load_catalog(path: str | Path = CATALOG_PATH) -> list[dict[str, Any]]:
    catalog_path = Path(path)
    if not catalog_path.exists():
        raise CatalogLoadError(f"Krea moodboard catalog not found: {catalog_path}")
    items = _load_catalog_file(catalog_path, default_collection="krea")
    # The Andro.Meta curated moods ship alongside the Krea catalog when present.
    if catalog_path == CATALOG_PATH and ANDROMETA_CATALOG_PATH.exists():
        try:
            items.extend(_load_catalog_file(ANDROMETA_CATALOG_PATH, default_collection="andrometa"))
        except CatalogLoadError:
            pass
    return items


def thumbnail_variant(url: str, size: int = THUMB_SIZE) -> str:
    """Rewrite a Krea CDN image URL to a smaller size variant.

    Krea's optim-images CDN serves the same image at 32/64/128/256/512/1024 via
    the trailing `-<size>.webp` segment; catalog URLs are usually 1024 (~80KB)
    which is wasteful for 112px browser cards (256 is ~3KB).
    """
    value = str(url or "")
    if not value.startswith("https://optim-images.krea.ai/"):
        return value
    return re.sub(r"-(\d{2,4})\.webp$", f"-{int(size)}.webp", value)


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
    return matches[: max(1, min(int(top_k or 5), len(catalog)))]


def catalog_listing(
    catalog: list[dict[str, Any]],
    *,
    query: str = "",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, str]:
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(int(page_size or 25), 100))
    if str(query or "").strip():
        matches = search_boards(catalog, query, top_k=min(max(safe_page * safe_page_size, safe_page_size), 100), min_score=1)
        items = [match["board"] for match in matches]
    else:
        items = sorted(catalog, key=lambda board: str(board.get("title") or ""))
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    page_items = items[start:start + safe_page_size]
    rows = [_catalog_row(board, index=start + idx + 1) for idx, board in enumerate(page_items)]
    text = "\n\n".join(rows) if rows else "No Krea moodboards matched this query."
    payload = {
        "query": str(query or ""),
        "page": safe_page,
        "page_size": safe_page_size,
        "total": total,
        "items": [_catalog_item_summary(board) for board in page_items],
    }
    return {
        "catalog_text": text,
        "catalog_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
    }


def catalog_cards(
    catalog: list[dict[str, Any]],
    *,
    query: str = "",
    limit: int = 60,
    offset: int = 0,
    family: str = "",
) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 60), 250))
    safe_offset = max(0, int(offset or 0))
    safe_family = str(family or "").strip().lower()
    if safe_family:
        if safe_family == "andrometa":
            pool = [board for board in catalog if str(board.get("collection") or "krea") == "andrometa"]
        else:
            pool = [board for board in catalog if style_family(board) == safe_family]
    else:
        pool = catalog
    if str(query or "").strip():
        matches = search_boards(pool, query, top_k=len(pool) or 1, min_score=1)
        all_items = [match["board"] for match in matches]
    else:
        all_items = sorted(pool, key=lambda board: str(board.get("title") or ""))
    items = all_items[safe_offset:safe_offset + safe_limit]
    return {
        "query": str(query or ""),
        "limit": safe_limit,
        "offset": safe_offset,
        "family": safe_family,
        "total": len(all_items),
        "items": [_catalog_card(board) for board in items],
    }


def catalog_cards_by_uuid(catalog: list[dict[str, Any]], uuids: list[str]) -> dict[str, Any]:
    by_uuid = {str(board.get("uuid") or ""): board for board in catalog}
    items = [
        _catalog_card(by_uuid[uuid])
        for uuid in [str(value or "").strip() for value in uuids]
        if uuid in by_uuid
    ]
    return {"total": len(items), "items": items}


def random_board(
    catalog: list[dict[str, Any]],
    *,
    seed: int,
    query: str = "",
    random_from_top_k: int = 0,
    min_score: int = 1,
    random_mode: str = "balanced",
) -> dict[str, Any]:
    pool = catalog
    if query.strip():
        top_k = random_from_top_k if random_from_top_k > 0 else 25
        matches = search_boards(catalog, query, top_k=top_k, min_score=min_score)
        pool = [match["board"] for match in matches]
    if not pool:
        raise ValueError("No Krea moodboards matched the query.")
    rng = random.Random(int(seed))
    if random_mode == "any":
        return rng.choice(pool)
    if random_mode == "photo":
        filtered = [board for board in pool if style_family(board) == "photo"]
        return rng.choice(filtered or pool)
    if random_mode == "non_photo":
        filtered = [board for board in pool if style_family(board) != "photo"]
        return rng.choice(filtered or pool)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for board in pool:
        grouped.setdefault(style_family(board), []).append(board)
    family = rng.choice(sorted(grouped))
    return rng.choice(grouped[family])


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


def resolve_board_reference(catalog: list[dict[str, Any]], value: str) -> dict[str, Any]:
    """Resolve title/search text, slug, UUID, URL, or metadata_json into a board."""
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Provide a moodboard title, search text, URL, UUID, slug, or metadata_json.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return find_board(catalog, raw)
    if not isinstance(data, dict):
        return find_board(catalog, raw)
    for key in ("uuid", "url", "slug", "title"):
        candidate = str(data.get(key) or "").strip()
        if candidate:
            try:
                return find_board(catalog, candidate)
            except ValueError:
                continue
    return find_board(catalog, raw)


def _merged_style_terms(board: dict[str, Any], prompt_guidance: str) -> list[str]:
    """Sanitized keywords + style axes, deduped against the prose and each other."""
    guidance_low = prompt_guidance.lower()
    merged: list[str] = []
    seen: set[str] = set()
    for raw_term in [*_string_list(board.get("keywords")), *_string_list(_guidance(board).get("style_axes"))]:
        term = sanitize_style_fragment(raw_term)
        key = term.lower()
        if not term or key in seen or key in guidance_low:
            continue
        seen.add(key)
        merged.append(term)
    return merged


def style_from_board(
    board: dict[str, Any],
    *,
    strength: str = "normal",
    include_guardrail: bool = True,
) -> dict[str, str]:
    guidance = _guidance(board)
    title = str(board.get("title") or "Krea Moodboard").strip()
    prompt_guidance = _sentence(abstract_style_prose(str(guidance.get("prompt_guidance") or "")))
    style_terms = _merged_style_terms(board, prompt_guidance)

    if strength == "concise":
        parts = [prompt_guidance]
    elif strength == "strong":
        parts = [
            f"{title}: {prompt_guidance}",
            _sentence(sanitize_style_prose(str(board.get("taste_profile") or ""))),
            f"Style keywords: {', '.join(style_terms)}." if style_terms else "",
        ]
    else:
        parts = [
            f"{title}: {prompt_guidance}",
            f"Style keywords: {', '.join(style_terms)}." if style_terms else "",
        ]
    body = " ".join(part for part in parts if part).strip()
    positive = f"{STYLE_GUARDRAIL} {body}" if include_guardrail else body
    negative = sanitize_negative_guidance(str(guidance.get("negative_guidance") or ""))
    metadata = {
        "title": title,
        "uuid": str(board.get("uuid") or ""),
        "slug": str(board.get("slug") or ""),
        "url": str(board.get("url") or ""),
        "keywords": _string_list(board.get("keywords")),
        "style_axes": _string_list(guidance.get("style_axes")),
        "source_summary": str(guidance.get("source_summary") or ""),
    }
    return {
        "positive": _sentence(positive),
        "negative": _sentence(negative) if negative else "",
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
    # Strongest style leads the blend text so it carries the most prompt weight.
    weighted = sorted(
        (
            (float(clean_weights[index]) if index < len(clean_weights) else 1.0, board)
            for index, board in enumerate(boards[:4])
        ),
        key=lambda pair: -pair[0],
    )
    positives: list[str] = []
    negatives: list[str] = []
    style_axes: list[str] = []
    sources: list[dict[str, str]] = []

    for weight, board in weighted:
        # Guardrail is prepended once for the whole mashup, not per board.
        style = style_from_board(board, strength=strength, include_guardrail=False)
        title = style["title"]
        positives.append(f"{title} (weight {weight:.2f}): {style['positive']}")
        if style["negative"]:
            negatives.append(style["negative"])
        metadata = json.loads(style["metadata_json"])
        for axis in metadata.get("style_axes", []):
            if axis and axis not in style_axes:
                style_axes.append(axis)
        sources.append({"title": title, "url": metadata.get("url", ""), "uuid": metadata.get("uuid", ""), "weight": f"{weight:.2f}"})

    source_titles = [source["title"] for source in sources]
    mashup_title = "Mashup: " + " + ".join(source_titles[:4])
    metadata = {"source_count": len(sources), "sources": sources, "style_axes": style_axes}
    preview = "\n".join(
        f"{idx}. {source['title']} (weight {source['weight']}) | {source['url']}"
        for idx, source in enumerate(sources, start=1)
    )
    return {
        "positive": f"{STYLE_GUARDRAIL} Blend these Krea moodboard styles: " + " | ".join(positives),
        "negative": ", ".join(_dedupe(negatives)),
        "title": mashup_title,
        "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
        "preview": (
            "Mashup sources resolved. Paste metadata_json from Search/Random/Style nodes, "
            "or type a moodboard title, search phrase, UUID, slug, or Krea URL.\n"
            f"{preview}"
        ),
    }


def style_family(board: dict[str, Any]) -> str:
    text = " ".join(_search_fields(board).values()).lower()
    for family, terms in STYLE_FAMILY_TERMS:
        if any(term in text for term in terms):
            return family
    return "other"


def cached_thumbnail_path(
    catalog: list[dict[str, Any]],
    uuid: str,
    *,
    cache_dir: Path = THUMB_CACHE_DIR,
    size: int = THUMB_SIZE,
    timeout: int = 20,
) -> Path:
    """Download a board's small thumbnail once and serve it from local disk.

    Keeps the repo image-free: thumbnails live only in the user's local cache
    (~3KB each at 256px), fetched lazily as boards are browsed.
    """
    clean_uuid = str(uuid or "").strip()
    board = next((b for b in catalog if str(b.get("uuid") or "") == clean_uuid), None)
    if board is None:
        raise ValueError(f"Unknown moodboard uuid: {clean_uuid}")
    url = thumbnail_variant(str(board.get("primary_image_url") or ""), size)
    if not url.startswith("https://optim-images.krea.ai/"):
        raise ValueError("Moodboard has no Krea thumbnail.")
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{clean_uuid}-{int(size)}.webp"
    if path.exists() and path.stat().st_size > 0:
        return path
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "comfyui-krea-moodboards/0.2 thumb cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data:
        raise ValueError("Empty thumbnail response.")
    path.write_bytes(data)
    return path


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


def _catalog_item_summary(board: dict[str, Any]) -> dict[str, Any]:
    guidance = _guidance(board)
    return {
        "title": str(board.get("title") or ""),
        "uuid": str(board.get("uuid") or ""),
        "slug": str(board.get("slug") or ""),
        "url": str(board.get("url") or ""),
        "thumbnail_url": thumbnail_variant(str(board.get("primary_image_url") or "")),
        "keywords": _string_list(board.get("keywords")),
        "style_axes": _string_list(guidance.get("style_axes")),
        "source_summary": str(guidance.get("source_summary") or ""),
        "family": style_family(board),
        "collection": str(board.get("collection") or "krea"),
    }


def _catalog_card(board: dict[str, Any]) -> dict[str, Any]:
    summary = _catalog_item_summary(board)
    style = style_from_board(board, strength="normal")
    summary.update(
        {
            "metadata_json": style["metadata_json"],
            "positive": style["positive"],
            "negative": style["negative"],
        }
    )
    return summary


def _catalog_row(board: dict[str, Any], *, index: int) -> str:
    summary = _catalog_item_summary(board)
    keywords = ", ".join(summary["keywords"][:6]) or "none"
    axes = ", ".join(summary["style_axes"][:6]) or "none"
    # Many official Krea boards share a title; the summary line disambiguates.
    board_summary = _normalize_spaces(summary.get("source_summary") or "")
    summary_line = f"\n   Summary: {board_summary}" if board_summary else ""
    return (
        f"{index}. [{summary['title']}]({summary['url']})\n"
        f"   Copy into board_1-board_4: {summary['uuid']}\n"
        f"   UUID: {summary['uuid']}\n"
        f"   Slug: {summary['slug']}\n"
        f"   Keywords: {keywords}\n"
        f"   Style axes: {axes}{summary_line}"
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

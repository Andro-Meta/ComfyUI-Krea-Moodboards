from __future__ import annotations

try:
    from .nodes import (
        KreaMoodboardApply,
        KreaMoodboardCatalogBrowser,
        KreaMoodboardMashup,
        KreaMoodboardRandom,
        KreaMoodboardSearch,
        KreaMoodboardStyle,
        KreaMoodboardVisualBrowser,
    )
except ImportError:
    import importlib.util
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("_krea_moodboards_nodes", root / "nodes.py")
    if spec is None or spec.loader is None:
        raise
    _nodes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_nodes)
    KreaMoodboardApply = _nodes.KreaMoodboardApply
    KreaMoodboardCatalogBrowser = _nodes.KreaMoodboardCatalogBrowser
    KreaMoodboardMashup = _nodes.KreaMoodboardMashup
    KreaMoodboardRandom = _nodes.KreaMoodboardRandom
    KreaMoodboardSearch = _nodes.KreaMoodboardSearch
    KreaMoodboardStyle = _nodes.KreaMoodboardStyle
    KreaMoodboardVisualBrowser = _nodes.KreaMoodboardVisualBrowser


NODE_CLASS_MAPPINGS = {
    "KreaMoodboardStyle": KreaMoodboardStyle,
    "KreaMoodboardCatalogBrowser": KreaMoodboardCatalogBrowser,
    "KreaMoodboardVisualBrowser": KreaMoodboardVisualBrowser,
    "KreaMoodboardSearch": KreaMoodboardSearch,
    "KreaMoodboardRandom": KreaMoodboardRandom,
    "KreaMoodboardMashup": KreaMoodboardMashup,
    "KreaMoodboardApply": KreaMoodboardApply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KreaMoodboardStyle": "Krea Moodboard Style",
    "KreaMoodboardCatalogBrowser": "Krea Moodboard Catalog Browser",
    "KreaMoodboardVisualBrowser": "Krea Moodboard Visual Browser",
    "KreaMoodboardSearch": "Krea Moodboard Search",
    "KreaMoodboardRandom": "Krea Moodboard Random",
    "KreaMoodboardMashup": "Krea Moodboard Mashup",
    "KreaMoodboardApply": "Krea Moodboard Apply",
}

WEB_DIRECTORY = "./web/js"

try:
    from aiohttp import web
    from server import PromptServer

    try:
        from .moodboard_catalog import CATALOG_PATH, catalog_cards, load_catalog
    except ImportError:
        from moodboard_catalog import CATALOG_PATH, catalog_cards, load_catalog

    @PromptServer.instance.routes.get("/krea_moodboards/catalog")
    async def krea_moodboards_catalog(request):
        query = request.rel_url.query.get("query", "")
        limit = int(request.rel_url.query.get("limit", 80))
        offset = int(request.rel_url.query.get("offset", 0))
        return web.json_response(catalog_cards(load_catalog(CATALOG_PATH), query=query, limit=limit, offset=offset))
except Exception:
    pass

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

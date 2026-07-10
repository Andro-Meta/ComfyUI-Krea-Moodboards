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
        from .moodboard_catalog import CATALOG_PATH, cached_thumbnail_path, catalog_cards, catalog_cards_by_uuid, load_catalog
    except ImportError:
        from moodboard_catalog import CATALOG_PATH, cached_thumbnail_path, catalog_cards, catalog_cards_by_uuid, load_catalog

    def _int_param(request, name: str, default: int) -> int:
        try:
            return int(request.rel_url.query.get(name, default))
        except (TypeError, ValueError):
            return default

    @PromptServer.instance.routes.get("/krea_moodboards/catalog")
    async def krea_moodboards_catalog(request):
        query = request.rel_url.query.get("query", "")
        family = request.rel_url.query.get("family", "")
        limit = _int_param(request, "limit", 80)
        offset = _int_param(request, "offset", 0)
        return web.json_response(
            catalog_cards(load_catalog(CATALOG_PATH), query=query, limit=limit, offset=offset, family=family)
        )

    @PromptServer.instance.routes.get("/krea_moodboards/by_uuid")
    async def krea_moodboards_by_uuid(request):
        uuids = [value for value in request.rel_url.query.get("uuids", "").split(",") if value]
        return web.json_response(catalog_cards_by_uuid(load_catalog(CATALOG_PATH), uuids))

    @PromptServer.instance.routes.get("/krea_moodboards/thumb")
    async def krea_moodboards_thumb(request):
        import asyncio

        uuid = request.rel_url.query.get("uuid", "")
        try:
            loop = asyncio.get_event_loop()
            path = await loop.run_in_executor(None, lambda: cached_thumbnail_path(load_catalog(CATALOG_PATH), uuid))
        except Exception as exc:
            return web.json_response({"error": str(exc)}, status=404)
        return web.FileResponse(path, headers={"Cache-Control": "max-age=86400"})
except Exception:
    pass

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

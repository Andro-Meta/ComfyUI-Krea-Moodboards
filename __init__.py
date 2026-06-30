from __future__ import annotations

try:
    from .nodes import (
        KreaMoodboardApply,
        KreaMoodboardCatalogBrowser,
        KreaMoodboardMashup,
        KreaMoodboardRandom,
        KreaMoodboardSearch,
        KreaMoodboardStyle,
    )
except ImportError:
    from nodes import (
        KreaMoodboardApply,
        KreaMoodboardCatalogBrowser,
        KreaMoodboardMashup,
        KreaMoodboardRandom,
        KreaMoodboardSearch,
        KreaMoodboardStyle,
    )


NODE_CLASS_MAPPINGS = {
    "KreaMoodboardStyle": KreaMoodboardStyle,
    "KreaMoodboardCatalogBrowser": KreaMoodboardCatalogBrowser,
    "KreaMoodboardSearch": KreaMoodboardSearch,
    "KreaMoodboardRandom": KreaMoodboardRandom,
    "KreaMoodboardMashup": KreaMoodboardMashup,
    "KreaMoodboardApply": KreaMoodboardApply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KreaMoodboardStyle": "Krea Moodboard Style",
    "KreaMoodboardCatalogBrowser": "Krea Moodboard Catalog Browser",
    "KreaMoodboardSearch": "Krea Moodboard Search",
    "KreaMoodboardRandom": "Krea Moodboard Random",
    "KreaMoodboardMashup": "Krea Moodboard Mashup",
    "KreaMoodboardApply": "Krea Moodboard Apply",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

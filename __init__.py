from __future__ import annotations

try:
    from .nodes import (
        KreaMoodboardApply,
        KreaMoodboardMashup,
        KreaMoodboardRandom,
        KreaMoodboardSearch,
        KreaMoodboardStyle,
    )
except ImportError:
    from nodes import (
        KreaMoodboardApply,
        KreaMoodboardMashup,
        KreaMoodboardRandom,
        KreaMoodboardSearch,
        KreaMoodboardStyle,
    )


NODE_CLASS_MAPPINGS = {
    "KreaMoodboardStyle": KreaMoodboardStyle,
    "KreaMoodboardSearch": KreaMoodboardSearch,
    "KreaMoodboardRandom": KreaMoodboardRandom,
    "KreaMoodboardMashup": KreaMoodboardMashup,
    "KreaMoodboardApply": KreaMoodboardApply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KreaMoodboardStyle": "Krea Moodboard Style",
    "KreaMoodboardSearch": "Krea Moodboard Search",
    "KreaMoodboardRandom": "Krea Moodboard Random",
    "KreaMoodboardMashup": "Krea Moodboard Mashup",
    "KreaMoodboardApply": "Krea Moodboard Apply",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

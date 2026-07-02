from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


KEEP_FIELDS = ("url", "slug", "uuid", "title", "taste_profile", "keywords", "primary_image_url", "qwen_guidance")
GUIDANCE_FIELDS = (
    "prompt_guidance",
    "negative_guidance",
    "style_axes",
    "conditioning_notes",
    "source_summary",
    "guidance_version",
    "guidance_backend",
)


def build_slim_catalog(source_path: Path, output_path: Path) -> int:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    items = payload.get("moodboards", payload if isinstance(payload, list) else [])
    if not isinstance(items, list):
        raise ValueError("Source catalog must contain a moodboards list.")

    slim_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        guidance = item.get("qwen_guidance")
        if not isinstance(guidance, dict) or not str(guidance.get("prompt_guidance") or "").strip():
            continue
        slim = {field: item.get(field) for field in KEEP_FIELDS if field in item}
        slim["keywords"] = [str(v).strip() for v in slim.get("keywords", []) if str(v).strip()]
        slim["qwen_guidance"] = {
            field: guidance.get(field)
            for field in GUIDANCE_FIELDS
            if field in guidance and guidance.get(field) not in (None, "", [])
        }
        slim_items.append(slim)

    output = {
        "version": int(payload.get("version") or 1) if isinstance(payload, dict) else 1,
        "source": payload.get("source", "") if isinstance(payload, dict) else "",
        "moodboards": slim_items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(slim_items)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the slim prompt-only Krea moodboard catalog.")
    parser.add_argument("source", type=Path, help="Path to the enriched Krea moodboard seed JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "krea_moodboards_slim.json",
        help="Output path for the slim catalog.",
    )
    args = parser.parse_args()

    count = build_slim_catalog(args.source, args.output)
    print(f"Wrote {count} Krea moodboards to {args.output}")


if __name__ == "__main__":
    main()

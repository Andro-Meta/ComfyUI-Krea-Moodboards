# ComfyUI Krea Moodboards

Prompt-only Krea moodboard nodes for ComfyUI. This pack ships 2500 enriched Krea moodboard prompt styles and helps you search, preview, randomize, mash up, and apply them before Krea 2 prompt enhancement or Qwen3-VL text encoding.

This is unofficial and is not affiliated with Krea AI.

## Quick Start

For one moodboard style:

1. Add `Krea Moodboard Search`.
2. Type a style idea, for example `dark teal gothic`, `anime`, or `warm pastel product`.
3. Add `Krea Moodboard Apply`.
4. Connect `Search.positive` to `Apply.moodboard_positive`.
5. Connect `Search.negative` to `Apply.moodboard_negative`.
6. Type your normal image prompt in `Apply.prompt`.
7. Connect `Apply.positive` to the Krea 2 workflow prompt input.

For a mashup:

1. Add `Krea Moodboard Catalog Browser`.
2. Search a style, for example `anime`.
3. Copy the UUID from `Copy into board_1-board_4: ...`.
4. Paste that UUID into `Krea Moodboard Mashup.board_1`.
5. Repeat for `board_2`, `board_3`, or `board_4`.
6. Check Mashup's `title` or `preview` output to see exactly which moodboards were selected.
7. Connect Mashup `positive` and `negative` into `Krea Moodboard Apply`.

## Where This Node Goes

Install this repo into:

```text
ComfyUI/custom_nodes/ComfyUI-Krea-Moodboards
```

In the official Krea 2 Turbo workflow, place these nodes at the prompt layer:

```text
Your user prompt
  -> Krea Moodboard Search or Random
  -> Krea Moodboard Apply
  -> Krea-2 Turbo subgraph Text String (User Prompt)
  -> optional prompt enhancement
  -> Qwen3-VL Krea2 text encode
  -> sampler
  -> Qwen Image VAE decode
```

These nodes do not load Krea 2, patch the model, emit conditioning tensors, download images, or replace the sampler. They output plain ComfyUI `STRING` values so they can feed the official Krea 2 workflow or a manual Krea2/Qwen3-VL graph.

## Visual Browsing

The package does not include Krea images. To visually browse the styles, open Krea's public moodboard gallery:

https://www.krea.ai/app?gallery=moodboards

Search or browse there, then use the same style names or aesthetic terms in `Krea Moodboard Search`. Each node returns `metadata_json` with the original Krea moodboard `url`, so you can click through and visually inspect the selected source moodboard.

## Nodes

### Krea Moodboard Catalog Browser

Lists moodboard names, UUIDs, keywords, style axes, and Krea source URLs.

Use this when you want to know exactly which UUID belongs to which moodboard, or when you want copyable links back to Krea:

```text
1. [Nostalgic Summer Anime](https://www.krea.ai/moodboard-feed/...)
   Copy into board_1-board_4: 57ad8374-9898-59aa-85ea-ec37b6947d8c
   UUID: 57ad8374-9898-59aa-85ea-ec37b6947d8c
   Slug: nostalgic-summer-anime-57ad8374-9898-59aa-85ea-ec37b6947d8c
   Keywords: nostalgic anime, warm summer, ...
```

Inputs:

- `query`: optional search text. Leave blank to browse alphabetically.
- `page`: page number.
- `page_size`: results per page.

Outputs:

- `catalog_text`: readable Markdown-style list with names, UUIDs, and full URLs.
- `catalog_json`: structured JSON for copying into other tools.

To use a result in Mashup, copy only the UUID after `Copy into board_1-board_4:` and paste it into `Krea Moodboard Mashup.board_1`, `board_2`, `board_3`, or `board_4`.

### Krea Moodboard Search

Searches all 2500 styles by title, keyword, taste profile, prompt guidance, style axes, conditioning notes, source summary, and negative guidance.

Useful queries:

```text
dark teal gothic
warm pastel product
grainy documentary
luminous anime landscape
retro cyberpunk poster
```

Outputs:

- `positive`: moodboard style text
- `negative`: moodboard negative guidance
- `title`: selected moodboard title
- `metadata_json`: source URL, UUID, slug, keywords, style axes, summary
- `preview`: top matches with scores and URLs

Search is dependency-free but weighted and synonym-aware, so common words like `dark`, `photo`, `bright`, `anime`, and `retro` can find Krea-style wording such as `noir`, `documentary`, `luminous`, `manga`, and `vintage`.

### Krea Moodboard Apply

Combines your user prompt with moodboard style text. This should usually feed the official Krea 2 workflow's `Text String (User Prompt)` input.

Use `style_only` if you want to feed the moodboard text into another prompt enhancement setup manually.

### Krea Moodboard Random

Picks a deterministic random style by seed. By default it uses `random_mode = balanced`, which samples a style family first so the largest family in the catalog, especially photo-like boards, does not dominate random results.

Random modes:

- `balanced`: recommended default; samples across style families first.
- `any`: pure random from the whole matching pool.
- `non_photo`: avoids boards classified as photo-family when possible.
- `photo`: only photo-family boards when possible.

Add a query to randomize within a style family, for example `query = cinematic noir` and `random_from_top_k = 25`.

### Krea Moodboard Mashup

Blends two to four moodboards by concatenating transferable style guidance, deduping style axes and negative guidance.

What to put in each `board` box:

- Best option: paste or connect the `metadata_json` output from `Krea Moodboard Search`, `Krea Moodboard Random`, or `Krea Moodboard Style`.
- Also works: a moodboard title, search phrase, UUID, slug, or Krea moodboard URL.

Examples:

```text
Abyssal Gothic
warm pastel product
https://www.krea.ai/moodboard-feed/...
{"uuid": "f8ba7b69-987b-5cc3-abd8-fc734a82223a"}
```

The `preview` output lists which source moodboards were resolved. If the mashup looks wrong, check `preview` first and make the board boxes more specific.

### Krea Moodboard Style

Looks up one moodboard by exact title, slug, UUID, URL, or search phrase. This avoids a 2500-item dropdown while keeping every option findable.

## Recommended Krea 2 Wiring

### Official Turbo Workflow

1. Load the official Krea 2 Turbo workflow from ComfyUI's template library.
2. Add `Krea Moodboard Search`.
3. Add `Krea Moodboard Apply`.
4. Connect your normal prompt to `Krea Moodboard Apply.prompt`.
5. Connect `Krea Moodboard Search.positive` to `Krea Moodboard Apply.moodboard_positive`.
6. Connect `Krea Moodboard Search.negative` to `Krea Moodboard Apply.moodboard_negative`.
7. Connect `Krea Moodboard Apply.positive` to the Krea-2 Turbo subgraph `Text String (User Prompt)` input.
8. If your workflow exposes a negative prompt or CFG path, connect `Krea Moodboard Apply.negative` there. If it does not, leave it unused.

For mashups, use two or more `Krea Moodboard Search` or `Krea Moodboard Random` nodes, then connect their `metadata_json` outputs into `Krea Moodboard Mashup.board_1`, `board_2`, etc. Connect the Mashup `positive` and `negative` outputs into `Krea Moodboard Apply`.

### Manual Krea 2 Graph

Use these nodes before Krea text encoding:

```text
UNETLoader -> Krea 2 model
CLIPLoader -> Qwen3-VL text encoder with Krea2 type
VAELoader -> Qwen Image VAE
Krea Moodboard Apply.positive -> Krea2/Qwen3-VL text encode prompt
encoded conditioning -> KSampler
KSampler samples -> VAE Decode
```

## Install

Install from ComfyUI-Manager / Comfy Registry by searching:

```text
Krea Moodboards
```

or:

```text
comfyui-krea-moodboards
```

Manual install:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Andro-Meta/ComfyUI-Krea-Moodboards.git
```

Restart ComfyUI. The nodes appear under:

```text
Krea / Moodboards
```

There are no required Python dependencies beyond the standard library.

## Catalog

The bundled catalog is:

```text
data/krea_moodboards_slim.json
```

It contains:

- `url`
- `slug`
- `uuid`
- `title`
- `taste_profile`
- `keywords`
- `qwen_guidance`

It intentionally does not contain moodboard images or image URLs.

To regenerate it from an enriched seed:

```bash
python tools/build_slim_catalog.py "path/to/krea_moodboards_seed.json"
```

## Development

Run tests:

```bash
python -m pytest
```

Run a quick import smoke check:

```bash
python -c "import importlib.util; spec=importlib.util.spec_from_file_location('krea_moodboards', '__init__.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m.NODE_DISPLAY_NAME_MAPPINGS)"
```

## Attribution

Krea 2 and Krea moodboards are by Krea AI. ComfyUI is by the ComfyUI project. This repository is an unofficial community prompt utility and does not bundle Krea images or model weights.

# ComfyUI Krea Moodboards

Prompt-only Krea moodboard nodes for ComfyUI. This pack ships 2500 enriched Krea moodboard prompt styles and helps you search, preview, randomize, mash up, and apply them before Krea 2 prompt enhancement or Qwen3-VL text encoding.

This is unofficial and is not affiliated with Krea AI.

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

Picks a deterministic random style by seed. Add a query to randomize within a style family, for example `query = cinematic noir` and `random_from_top_k = 25`.

### Krea Moodboard Mashup

Blends two to four moodboards by concatenating transferable style guidance, deduping style axes and negative guidance.

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

Once published, the easiest install path should be ComfyUI-Manager's node search. Search for:

```text
Krea Moodboards
```

or:

```text
comfyui-krea-moodboards
```

Until it is published to the Comfy Registry, clone or copy this folder into ComfyUI:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Andro-Meta/ComfyUI-Krea-Moodboards.git
```

Restart ComfyUI. The nodes appear under:

```text
Krea / Moodboards
```

There are no required Python dependencies beyond the standard library.

## Comfy Registry And Manager

ComfyUI's current community node discovery path is the Comfy Registry, which powers the new ComfyUI-Manager install UI. This repo includes registry-ready metadata in `pyproject.toml` and a publish workflow in `.github/workflows/publish-comfy-registry.yml`.

Before publishing, update:

- `pyproject.toml` repository URLs
- `pyproject.toml` `[tool.comfy].PublisherId`
- GitHub repository secret `REGISTRY_ACCESS_TOKEN`

See `PUBLISHING.md` for the full Registry path and the optional legacy ComfyUI-Manager `custom-node-list.json` entry.

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

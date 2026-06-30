# Publishing To ComfyUI Node Discovery

ComfyUI's current node discovery flow is the Comfy Registry, which powers the new ComfyUI-Manager install UI. The older ComfyUI-Manager `custom-node-list.json` flow still exists for legacy compatibility.

## Current Recommended Path: Comfy Registry

1. Push this project to the public GitHub repo.
2. Confirm the Comfy Registry publisher exists.
3. Confirm `pyproject.toml` has the live repository and publisher metadata:

```toml
[project.urls]
Homepage = "https://github.com/Andro-Meta/ComfyUI-Krea-Moodboards"
Repository = "https://github.com/Andro-Meta/ComfyUI-Krea-Moodboards"
Issues = "https://github.com/Andro-Meta/ComfyUI-Krea-Moodboards/issues"

[tool.comfy]
PublisherId = "andrometa"
DisplayName = "Krea Moodboards"
```

4. Create a Registry API key for that publisher.
5. Publish manually:

```bash
comfy node publish
```

Or publish with GitHub Actions by adding a repository secret named:

```text
REGISTRY_ACCESS_TOKEN
```

Then run the included workflow from GitHub Actions.

Important:

- The `[project].name` value is the registry node ID and should be treated as permanent.
- Bump `[project].version` for every published update.
- Keep `requirements.txt` dependency-free unless a real runtime dependency is added.
- Keep `data/krea_moodboards_slim.json` bundled; the node needs it at runtime.

## Legacy ComfyUI-Manager List

If you also want legacy ComfyUI-Manager visibility, submit a PR to `Comfy-Org/ComfyUI-Manager` adding an entry similar to this in `custom-node-list.json`.

```json
{
  "author": "Andro-Meta",
  "title": "ComfyUI Krea Moodboards",
  "reference": "https://github.com/Andro-Meta/ComfyUI-Krea-Moodboards",
  "files": [
    "https://github.com/Andro-Meta/ComfyUI-Krea-Moodboards"
  ],
  "install_type": "git-clone",
  "description": "Prompt-only Krea moodboard search, random, mashup, and apply nodes for Krea 2 ComfyUI workflows.",
  "tags": [
    "prompt",
    "krea",
    "krea2",
    "moodboard",
    "style"
  ]
}
```

Before submitting the legacy Manager PR, test the local DB in ComfyUI-Manager if possible.

## Why Both Paths?

The new Manager UI searches the Comfy Registry for node packs and individual nodes. The legacy list is still useful for older Manager installs and users who have not moved fully to the registry-backed workflow.

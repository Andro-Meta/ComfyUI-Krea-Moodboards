# Data Notice

This repository includes a prompt-only catalog derived from public Krea moodboard pages and local prompt-style enrichment.

The bundled file is:

```text
data/krea_moodboards_slim.json
```

It includes moodboard metadata and prompt guidance:

- source Krea moodboard URL
- public Krea thumbnail URL
- slug and UUID
- title
- taste profile
- keywords
- prompt guidance
- negative guidance
- style axes
- conditioning notes
- source summary

The repository also bundles `data/andrometa_moodboards.json`, an original curated set of Andro.Meta prompt moods (text only).

It does not include:

- Krea moodboard images
- downloaded image files
- full image URL lists
- Krea model weights
- ComfyUI model weights

The visual browser downloads small (256px, ~3KB) public Krea thumbnails on demand into a local, git-ignored cache (`data/thumb_cache/`) on the user's machine. No images are committed to this repository or the registry package.

Users can visually inspect the source styles on Krea's public moodboard gallery:

https://www.krea.ai/app?gallery=moodboards

This project is unofficial and is not affiliated with, endorsed by, or sponsored by Krea AI.

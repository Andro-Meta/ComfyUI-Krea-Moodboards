import { app } from "../../scripts/app.js";

const FAVORITES_KEY = "krea_moodboards:favorites";

function widget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function setWidget(node, name, value) {
  const w = widget(node, name);
  if (!w) return;
  w.value = value ?? "";
  w.callback?.(w.value);
}

function getFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]");
  } catch {
    return [];
  }
}

function setFavorites(values) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([...new Set(values)]));
}

function css(el, styles) {
  Object.assign(el.style, styles);
  return el;
}

function text(tag, value, className) {
  const el = document.createElement(tag);
  el.textContent = value;
  if (className) el.className = className;
  return el;
}

async function fetchCards(query) {
  const url = `/krea_moodboards/catalog?query=${encodeURIComponent(query || "")}&limit=120`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
  return response.json();
}

function selectedUuid(node) {
  return widget(node, "selected_uuid")?.value || "";
}

function buildBrowser(node) {
  const root = css(document.createElement("div"), {
    fontFamily: "Arial, sans-serif",
    color: "var(--fg-color, #ddd)",
    background: "var(--comfy-input-bg, #222)",
    border: "1px solid var(--border-color, #444)",
    borderRadius: "8px",
    padding: "8px",
    width: "100%",
    boxSizing: "border-box",
  });

  const controls = css(document.createElement("div"), {
    display: "grid",
    gridTemplateColumns: "1fr auto auto",
    gap: "6px",
    marginBottom: "8px",
  });
  const search = css(document.createElement("input"), {
    minWidth: "0",
    padding: "6px",
    borderRadius: "6px",
    border: "1px solid #555",
    background: "#111",
    color: "#eee",
  });
  search.placeholder = "Search Krea moodboards...";
  search.value = widget(node, "query")?.value || "";
  const reload = text("button", "Search");
  const favsOnly = text("button", "Favorites");
  controls.append(search, reload, favsOnly);

  const selected = css(text("div", "No moodboard selected."), {
    margin: "4px 0 8px",
    fontSize: "12px",
    color: "#b8c7ff",
  });
  const grid = css(document.createElement("div"), {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(112px, 1fr))",
    gap: "8px",
    maxHeight: "360px",
    overflow: "auto",
  });
  root.append(controls, selected, grid);

  let cards = [];
  let showingFavorites = false;

  function updateSelectedText() {
    const title = widget(node, "selected_title")?.value || "";
    const uuid = selectedUuid(node);
    selected.textContent = uuid ? `Selected: ${title} (${uuid})` : "No moodboard selected.";
  }

  function selectCard(card) {
    setWidget(node, "query", search.value);
    setWidget(node, "selected_uuid", card.uuid);
    setWidget(node, "selected_title", card.title);
    setWidget(node, "selected_url", card.url);
    setWidget(node, "selected_metadata_json", card.metadata_json);
    updateSelectedText();
    render();
  }

  function toggleFavorite(uuid) {
    const favs = getFavorites();
    if (favs.includes(uuid)) setFavorites(favs.filter((v) => v !== uuid));
    else setFavorites([...favs, uuid]);
    render();
  }

  function render() {
    const favs = getFavorites();
    const visible = showingFavorites ? cards.filter((card) => favs.includes(card.uuid)) : cards;
    grid.replaceChildren();
    for (const card of visible) {
      const item = css(document.createElement("div"), {
        border: card.uuid === selectedUuid(node) ? "2px solid #8fb4ff" : "1px solid #555",
        borderRadius: "8px",
        overflow: "hidden",
        background: "#181818",
        cursor: "pointer",
      });
      const img = css(document.createElement("img"), {
        width: "100%",
        height: "82px",
        objectFit: "cover",
        display: "block",
        background: "#333",
      });
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      img.src = card.thumbnail_url || "";
      img.alt = card.title;
      img.onerror = () => {
        img.replaceWith(css(text("div", "No thumbnail"), {
          height: "82px",
          display: "grid",
          placeItems: "center",
          color: "#aaa",
          fontSize: "12px",
          background: "#333",
        }));
      };
      const body = css(document.createElement("div"), { padding: "6px" });
      const title = css(text("div", card.title), { fontSize: "12px", fontWeight: "bold", lineHeight: "1.2" });
      const keywords = css(text("div", (card.keywords || []).slice(0, 3).join(", ")), {
        fontSize: "10px",
        color: "#aaa",
        minHeight: "24px",
        marginTop: "4px",
      });
      const actions = css(document.createElement("div"), {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginTop: "5px",
      });
      const star = css(text("button", favs.includes(card.uuid) ? "★" : "☆"), {
        border: "0",
        background: "transparent",
        color: "#ffd15c",
        cursor: "pointer",
        fontSize: "16px",
      });
      const link = css(text("a", "Krea"), { color: "#8fb4ff", fontSize: "11px" });
      link.href = card.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      star.onclick = (event) => {
        event.stopPropagation();
        toggleFavorite(card.uuid);
      };
      actions.append(star, link);
      body.append(title, keywords, actions);
      item.append(img, body);
      item.onclick = () => selectCard(card);
      item.title = `${card.title}\nUUID: ${card.uuid}\n${card.url}`;
      grid.append(item);
    }
    if (!visible.length) grid.append(css(text("div", "No moodboards found."), { color: "#aaa", padding: "10px" }));
  }

  async function load() {
    showingFavorites = false;
    setWidget(node, "query", search.value);
    grid.replaceChildren(css(text("div", "Loading moodboards..."), { color: "#aaa", padding: "10px" }));
    try {
      const data = await fetchCards(search.value);
      cards = data.items || [];
      render();
    } catch (error) {
      grid.replaceChildren(css(text("div", String(error)), { color: "#ff8a8a", padding: "10px" }));
    }
  }

  reload.onclick = () => load();
  favsOnly.onclick = () => {
    showingFavorites = !showingFavorites;
    favsOnly.textContent = showingFavorites ? "All" : "Favorites";
    render();
  };
  search.addEventListener("keydown", (event) => {
    if (event.key === "Enter") load();
  });

  updateSelectedText();
  load();
  return root;
}

app.registerExtension({
  name: "andrometa.krea_moodboards.visual_browser",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "KreaMoodboardVisualBrowser") return;
    const original = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      original?.apply(this, arguments);
      for (const name of ["selected_uuid", "selected_title", "selected_url", "selected_metadata_json"]) {
        const w = widget(this, name);
        if (w) w.hidden = true;
      }
      this.addDOMWidget("browser", "KREA_MOODBOARD_BROWSER", buildBrowser(this), {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 430,
        getHeight: () => 430,
      });
      this.size = [Math.max(this.size?.[0] || 360, 420), Math.max(this.size?.[1] || 520, 560)];
    };
  },
});

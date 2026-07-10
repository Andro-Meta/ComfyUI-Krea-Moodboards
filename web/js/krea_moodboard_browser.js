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

const PAGE_SIZE = 90;
const FAMILIES = [
  ["", "All styles"],
  ["photo", "Photo"],
  ["cinematic", "Cinematic"],
  ["anime", "Anime"],
  ["illustration", "Illustration"],
  ["graphic", "Graphic"],
  ["abstract", "Abstract"],
  ["3d", "3D"],
  ["other", "Other"],
  ["andrometa", "Andro.Meta"],
];

async function fetchCards(query, offset = 0, family = "", limit = PAGE_SIZE) {
  const url = `/krea_moodboards/catalog?query=${encodeURIComponent(query || "")}&limit=${limit}&offset=${offset}&family=${encodeURIComponent(family || "")}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
  return response.json();
}

async function fetchFavoriteCards(uuids) {
  if (!uuids.length) return { total: 0, items: [] };
  const url = `/krea_moodboards/by_uuid?uuids=${encodeURIComponent(uuids.join(","))}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Favorites request failed: ${response.status}`);
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
    gridTemplateColumns: "1fr auto auto auto auto",
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
  const familySelect = css(document.createElement("select"), {
    padding: "6px",
    borderRadius: "6px",
    border: "1px solid #555",
    background: "#111",
    color: "#eee",
    maxWidth: "110px",
  });
  for (const [value, label] of FAMILIES) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    familySelect.append(option);
  }
  familySelect.title = "Filter by style family or the Andro.Meta curated collection.";
  const reload = text("button", "Search");
  const lucky = text("button", "🎲");
  lucky.title = "Pick a random moodboard from the current search/filter.";
  const favsOnly = text("button", "Favorites");
  controls.append(search, familySelect, reload, lucky, favsOnly);

  const selected = css(text("div", "No moodboard selected."), {
    margin: "4px 0 8px",
    fontSize: "12px",
    color: "#b8c7ff",
  });
  const status = css(text("div", ""), {
    margin: "0 0 8px",
    fontSize: "11px",
    color: "#aaa",
  });
  const grid = css(document.createElement("div"), {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(112px, 1fr))",
    gap: "8px",
    maxHeight: "360px",
    overflow: "auto",
  });
  const more = css(text("button", "Load more"), {
    display: "none",
    width: "100%",
    marginTop: "8px",
    padding: "6px",
  });
  root.append(controls, selected, status, grid, more);

  let cards = [];
  let showingFavorites = false;
  let favoriteCards = [];
  let total = 0;
  let currentQuery = search.value || "";
  let currentFamily = "";

  function cardMatchesQuery(card, query) {
    if (!query) return true;
    const haystack = [card.title, card.source_summary, (card.keywords || []).join(" "), (card.style_axes || []).join(" ")]
      .join(" ")
      .toLowerCase();
    return query.toLowerCase().split(/\s+/).every((term) => !term || haystack.includes(term));
  }

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
    // Favorites are searchable too: the search box filters them client-side.
    const visible = showingFavorites
      ? favoriteCards.filter((card) => cardMatchesQuery(card, search.value || ""))
      : cards;
    grid.replaceChildren();
    status.textContent = showingFavorites
      ? `Showing ${visible.length} of ${favoriteCards.length} saved favorite${favoriteCards.length === 1 ? "" : "s"}${search.value ? ` for "${search.value}"` : ""}.`
      : `Showing ${cards.length} of ${total} moodboards${currentQuery ? ` for "${currentQuery}"` : ""}${currentFamily ? ` in ${currentFamily}` : ""}.`;
    more.style.display = !showingFavorites && cards.length < total ? "block" : "none";
    for (const card of visible) {
      const item = css(document.createElement("div"), {
        border: card.uuid === selectedUuid(node) ? "2px solid #8fb4ff" : "1px solid #555",
        borderRadius: "8px",
        overflow: "hidden",
        background: "#181818",
        cursor: "pointer",
      });
      const placeholder = () => {
        const emoji = /^\p{Extended_Pictographic}/u.test(card.title) ? [...card.title][0] : "";
        return css(text("div", emoji || "No thumbnail"), {
          height: "82px",
          display: "grid",
          placeItems: "center",
          color: "#aaa",
          fontSize: emoji ? "34px" : "12px",
          background: "#333",
        });
      };
      let media;
      if (card.thumbnail_url) {
        const img = css(document.createElement("img"), {
          width: "100%",
          height: "82px",
          objectFit: "cover",
          display: "block",
          background: "#333",
        });
        img.loading = "lazy";
        img.referrerPolicy = "no-referrer";
        // Local disk-cached 256px thumb first (~3KB), CDN small variant fallback.
        img.src = card.uuid ? `/krea_moodboards/thumb?uuid=${encodeURIComponent(card.uuid)}` : card.thumbnail_url;
        img.alt = card.title;
        let triedCdn = false;
        img.onerror = () => {
          if (!triedCdn) {
            triedCdn = true;
            img.src = card.thumbnail_url;
            return;
          }
          img.replaceWith(placeholder());
        };
        media = img;
      } else {
        media = placeholder();
      }
      const body = css(document.createElement("div"), { padding: "6px" });
      const title = css(text("div", card.title), { fontSize: "12px", fontWeight: "bold", lineHeight: "1.2" });
      // Many boards share a title; the summary sentence tells them apart.
      const subtitleText = card.source_summary || (card.keywords || []).slice(0, 3).join(", ");
      const keywords = css(text("div", subtitleText), {
        fontSize: "10px",
        color: "#aaa",
        minHeight: "24px",
        maxHeight: "36px",
        overflow: "hidden",
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
      item.append(media, body);
      item.onclick = () => selectCard(card);
      item.title = `${card.title}\n${card.source_summary || ""}\nUUID: ${card.uuid}\n${card.url}`;
      grid.append(item);
    }
    if (!visible.length) grid.append(css(text("div", "No moodboards found."), { color: "#aaa", padding: "10px" }));
  }

  async function load({ append = false } = {}) {
    if (append && ((search.value || "") !== currentQuery || (familySelect.value || "") !== currentFamily)) {
      append = false;
    }
    showingFavorites = false;
    favsOnly.textContent = "Favorites";
    setWidget(node, "query", search.value);
    currentQuery = search.value || "";
    currentFamily = familySelect.value || "";
    if (!append) {
      cards = [];
      total = 0;
      grid.replaceChildren(css(text("div", "Loading moodboards..."), { color: "#aaa", padding: "10px" }));
      status.textContent = "";
      more.style.display = "none";
    } else {
      more.textContent = "Loading...";
      more.disabled = true;
    }
    try {
      const data = await fetchCards(currentQuery, append ? cards.length : 0, currentFamily);
      total = data.total || 0;
      cards = append ? [...cards, ...(data.items || [])] : (data.items || []);
      render();
    } catch (error) {
      grid.replaceChildren(css(text("div", String(error)), { color: "#ff8a8a", padding: "10px" }));
    } finally {
      more.textContent = "Load more";
      more.disabled = false;
    }
  }

  reload.onclick = () => load();
  familySelect.onchange = () => load();
  more.onclick = () => load({ append: true });
  // Infinite scroll: append the next page when the grid nears its bottom.
  // The Load more button remains as a manual fallback.
  let autoLoading = false;
  grid.addEventListener("scroll", async () => {
    if (autoLoading || showingFavorites) return;
    if (cards.length >= total || !cards.length) return;
    if (grid.scrollTop + grid.clientHeight < grid.scrollHeight - 160) return;
    autoLoading = true;
    try {
      await load({ append: true });
    } finally {
      autoLoading = false;
    }
  });
  lucky.onclick = async () => {
    // Random pick from everything matching the current search/filter, not
    // just the loaded page: fetch one card at a random offset.
    try {
      lucky.disabled = true;
      const probe = await fetchCards(search.value || "", 0, familySelect.value || "", 1);
      const poolTotal = probe.total || 0;
      if (!poolTotal) return;
      const offset = Math.floor(Math.random() * poolTotal);
      const pick = await fetchCards(search.value || "", offset, familySelect.value || "", 1);
      const card = (pick.items || [])[0];
      if (card) selectCard(card);
    } catch {
      /* leave current view untouched */
    } finally {
      lucky.disabled = false;
    }
  };
  favsOnly.onclick = async () => {
    showingFavorites = !showingFavorites;
    favsOnly.textContent = showingFavorites ? "All" : "Favorites";
    if (showingFavorites) {
      grid.replaceChildren(css(text("div", "Loading favorites..."), { color: "#aaa", padding: "10px" }));
      try {
        const data = await fetchFavoriteCards(getFavorites());
        favoriteCards = data.items || [];
      } catch (error) {
        grid.replaceChildren(css(text("div", String(error)), { color: "#ff8a8a", padding: "10px" }));
        return;
      }
    }
    render();
  };
  search.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      if (showingFavorites) render();
      else load();
    }
  });
  search.addEventListener("input", () => {
    // Favorites filter live as you type; the full catalog waits for Enter/Search.
    if (showingFavorites) render();
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
      for (const name of ["query", "selected_uuid", "selected_title", "selected_url", "selected_metadata_json"]) {
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

// BauRadar – Anzeige der täglichen Sammeldaten (items.json)
(function () {
  const KEY = { read: "bauradar.read", saved: "bauradar.saved", theme: "bauradar.theme" };
  const REGION_ORDER = { duesseldorf_dueren: 1, nrw: 2, de: 3 };
  const LABEL = { duesseldorf_dueren: "Düsseldorf/Düren", nrw: "NRW", de: "Deutschland" };

  let data = { news: [], tenders: [], region_labels: LABEL };
  let tab = "top";

  // localStorage kann fehlen (privates Fenster, blockierte Daten): dann bleibt die App ohne Merkliste nutzbar
  function load(key) {
    try { return new Set(JSON.parse(localStorage.getItem(key)) || []); } catch (e) { return new Set(); }
  }
  function save(key, set) {
    try { localStorage.setItem(key, JSON.stringify([...set])); } catch (e) { /* ignorieren */ }
  }
  const read = load(KEY.read);
  const saved = load(KEY.saved);

  const $ = (sel) => document.querySelector(sel);
  const feed = $("#feed");

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function fmtDate(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function countdown(deadline) {
    if (!deadline) return null;
    const end = new Date(deadline + "T23:59:59");
    const days = Math.ceil((end - new Date()) / 86400000);
    if (days < 0) return "Frist abgelaufen";
    if (days === 0) return "Frist heute";
    if (days === 1) return "noch 1 Tag";
    return `noch ${days} Tage`;
  }

  function regionBadge(region) {
    return el("span", "badge" + (region === "duesseldorf_dueren" ? " dd" : ""), LABEL[region] || "");
  }

  function matches(text) {
    const q = $("#search").value.trim().toLowerCase();
    return !q || text.toLowerCase().includes(q);
  }

  function newsCard(item) {
    const isRead = read.has(item.id);
    const isSaved = saved.has(item.id);
    const card = el("article", "card" + (isRead ? " read" : ""));

    const meta = el("div", "meta");
    meta.append(regionBadge(item.region), el("span", "", item.source), el("span", "", fmtDate(item.published)));
    card.append(meta);

    const title = el("a", "title", item.title);
    title.href = item.url;
    title.target = "_blank";
    title.rel = "noopener";
    title.addEventListener("click", () => toggle(read, KEY.read, item.id, true));
    card.append(title);

    if (item.ai_summary) {
      card.append(el("p", "text", item.ai_summary), el("div", "ai-note", "KI-Kurzfassung"));
    } else if (item.teaser) {
      card.append(el("p", "text", item.teaser));
    }

    card.append(actions(item, isRead, isSaved));
    return card;
  }

  function actions(item, isRead, isSaved) {
    const row = el("div", "actions");
    const readBtn = el("button", isRead ? "on" : "", isRead ? "✓ gelesen" : "Als gelesen");
    readBtn.type = "button";
    readBtn.addEventListener("click", () => toggle(read, KEY.read, item.id));
    const saveBtn = el("button", isSaved ? "on" : "", isSaved ? "★ gemerkt" : "☆ merken");
    saveBtn.type = "button";
    saveBtn.addEventListener("click", () => toggle(saved, KEY.saved, item.id));
    const open = el("a", "", "Original →");
    open.href = item.url;
    open.target = "_blank";
    open.rel = "noopener";
    row.append(readBtn, saveBtn, open);
    return row;
  }

  function tenderCard(t) {
    const card = el("article", "card");
    const meta = el("div", "meta");
    meta.append(regionBadge(t.region), el("span", "", t.city || ""));
    const cd = countdown(t.deadline);
    if (cd) meta.append(el("span", "badge deadline", cd));
    else meta.append(el("span", "", "Frist unbekannt"));
    card.append(meta);

    const title = el("a", "title", t.title);
    title.href = t.url;
    title.target = "_blank";
    title.rel = "noopener";
    card.append(title);

    const info = [t.buyer, t.deadline ? "Abgabe bis " + fmtDate(t.deadline + "T12:00:00") : null]
      .filter(Boolean).join(" · ");
    card.append(el("p", "text", info));
    card.append(actions(t, read.has(t.id), saved.has(t.id)));
    return card;
  }

  function toggle(set, key, id, markOnly) {
    if (markOnly) set.add(id); else if (set.has(id)) set.delete(id); else set.add(id);
    save(key, set);
    render();
  }

  function newTendersLast24h() {
    const since = Date.now() - 86400000;
    return data.tenders.filter((t) => t.first_seen && new Date(t.first_seen).getTime() >= since).length;
  }

  function render() {
    feed.textContent = "";
    const unreadOnly = $("#unreadOnly").checked;
    const savedOnly = $("#savedOnly").checked;

    if (tab === "tenders") {
      if (data.tenders.length === 0) feed.append(el("div", "empty", "Keine Ausschreibungen gefunden."));
      data.tenders
        .filter((t) => matches(`${t.title} ${t.buyer} ${t.city}`))
        .filter((t) => !savedOnly || saved.has(t.id))
        .filter((t) => !unreadOnly || !read.has(t.id))
        .forEach((t) => feed.append(tenderCard(t)));
      return;
    }

    if (tab === "top") {
      const tile = el("div", "tile");
      tile.append("Neue Ausschreibungen seit gestern: ", el("strong", "", String(newTendersLast24h())));
      feed.append(tile);
    }

    const items = data.news
      .filter((n) => tab === "top" || n.region === tab)
      .filter((n) => matches(`${n.title} ${n.teaser} ${n.source} ${n.ai_summary || ""}`))
      .filter((n) => !savedOnly || saved.has(n.id))
      .filter((n) => !unreadOnly || !read.has(n.id))
      .sort((a, b) => (REGION_ORDER[a.region] - REGION_ORDER[b.region]) || (b.published > a.published ? 1 : -1));

    if (items.length === 0) feed.append(el("div", "empty", "Nichts gefunden."));
    items.forEach((n) => feed.append(newsCard(n)));
  }

  function setStand() {
    $("#stand").textContent = data.generated_at ? `Stand: ${data.generated_at}` : "Stand unbekannt";
    if (data.errors && data.errors.length) {
      $("#stand").textContent += ` · ${data.errors.length} Quelle(n) nicht erreichbar`;
    }
  }

  function applyTheme() {
    let theme = null;
    try { theme = localStorage.getItem(KEY.theme); } catch (e) { /* ignorieren */ }
    if (theme) document.documentElement.dataset.theme = theme;
  }

  function toggleTheme() {
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const current = document.documentElement.dataset.theme || (dark ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem(KEY.theme, next); } catch (e) { /* ignorieren */ }
  }

  document.querySelectorAll("#tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      tab = btn.dataset.tab;
      document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b === btn));
      render();
      window.scrollTo({ top: 0 });
    });
  });
  ["#search", "#unreadOnly", "#savedOnly"].forEach((sel) => $(sel).addEventListener("input", render));
  $("#darkToggle").addEventListener("click", toggleTheme);

  applyTheme();
  fetch("items.json?v=" + Date.now(), { cache: "no-store" })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((json) => { data = json; setStand(); render(); })
    .catch(() => { $("#stand").textContent = "Daten konnten nicht geladen werden."; });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => { /* Offline-Modus optional */ });
  }
})();

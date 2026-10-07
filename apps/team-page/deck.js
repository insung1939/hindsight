/* 발표 페이지 — 숫자는 data/snapshot.json 을 먼저 쓰고, API 가 깨어 있으면 실시간 값으로 덮어쓴다. */
const CONFIG = {
  api: "https://hindsight-api-edab.onrender.com",  // Render 합본 API (서비스 4개를 한 프로세스에)
  web: "https://hindsight-web.vercel.app",          // Vercel 서비스
};
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = {
  n: (v) => (v == null ? "—" : Number(v).toLocaleString("ko-KR")),
  pct0: (v) => (v == null ? "—" : Math.round(v * 100) + "%"),
  pct1: (v) => (v == null ? "—" : (v > 0 ? "+" : "") + (v * 100).toFixed(1) + "%"),
  date: (v) => (v ? String(v).slice(0, 10) : ""),
  x: (v) => (v == null ? "—" : Number(v).toFixed(2) + "배"),
  pct1s: (v) => (v == null ? "—" : (v * 100).toFixed(1) + "%"),
};
const get = (o, path) => path.split(".").reduce((a, k) => (a == null ? undefined : a[k]), o);

// ── 주소 ──
$$("[data-url=web]").forEach((e) => (e.textContent = CONFIG.web.replace(/^https?:\/\//, "")));
$$("[data-url=docs]").forEach((e) => (e.textContent = CONFIG.api.replace(/^https?:\/\//, "") + "/docs"));
["btn-web", "btn-web2", "lnk-web"].forEach((id) => $("#" + id) && ($("#" + id).href = CONFIG.web));
["btn-docs", "btn-docs2", "lnk-docs"].forEach((id) => $("#" + id) && ($("#" + id).href = CONFIG.api + "/docs"));

// ── 데이터 바인딩 ──
function derive(d) {
  const m = d.market || {};
  const by = m.assets_by_market || {};
  m.assets_total = Object.values(by).reduce((a, v) => a + (v.total || 0), 0);
  m.tracked_total = Object.values(by).reduce((a, v) => a + (v.tracked || 0), 0);
  m.vol_share = m.prices ? m.prices_with_volume / m.prices : null;
  return d;
}
function bind(d) {
  $$("[data-bind]").forEach((el) => {
    const v = get(d, el.dataset.bind);
    const f = el.dataset.fmt;
    if (v == null) return;
    el.textContent = f ? fmt[f](v) : (typeof v === "number" ? fmt.n(v) : v);
  });
  renderOverall(d); renderHist(d); renderTables(d); renderFindings(d);
}
function card(label, value, sub, cls = "") {
  return `<div class="card"><h3>${label}</h3><div class="big ${cls}">${value}</div><p class="note">${sub || ""}</p></div>`;
}
function renderOverall(d) {
  const el = $("#overall-cards"); if (!el) return;
  const s = d.summary || {};
  el.innerHTML = [5, 20, 60].map((h) => {
    const v = s[`bull:overall:${h}`] || s[`overall:${h}`];
    if (!v || !v.n) return card(`${h}거래일 뒤`, "—", "표본 없음");
    const cls = v.mean > 0 ? "pos-v" : v.mean < 0 ? "neg-v" : "";
    return card(`${h}거래일 뒤 · n=${fmt.n(v.n)}`,
      `${fmt.pct1(v.mean)}<small>평균</small>`,
      `상승 <b>${fmt.pct0(v.win_rate)}</b> · 시장 대비 <b>${fmt.pct1(v.excess_mean)}</b>` + (v.vol_ratio_median ? ` · 거래량 <b>${v.vol_ratio_median}배</b>` : ""), cls);
  }).join("");
}
function renderHist(d) {
  const el = $("#hist-overall"); if (!el) return;
  const v = (d.summary || {})["bull:overall:20"] || (d.summary || {})["overall:20"]; if (!v || !v.histogram) return;
  const max = Math.max(1, ...v.histogram.map((b) => b.n));
  const label = (b) => (b.from <= -1 ? "< −20%" : b.to >= 9 ? "> +20%" : `${Math.round(b.from * 100)}~${Math.round(b.to * 100)}%`);
  el.innerHTML = v.histogram.map((b) => `<div class="c"><div class="n">${fmt.n(b.n)}</div><div class="b ${b.from >= 0 ? "up" : ""}" style="height:${(b.n / max) * 100}%"></div><div class="l">${label(b)}</div></div>`).join("");
}
function row(cells) { return `<tr>${cells.map((c, i) => `<td class="${i ? "r" : ""}">${c}</td>`).join("")}</tr>`; }
function renderTables(d) {
  const s = d.summary || {};
  const tm = $("#tbl-market tbody");
  if (tm) tm.innerHTML = [["전체", "bull:overall:20"], ["국내", "bull:market:KRX:20"], ["미국", "bull:market:US:20"], ["코인", "bull:market:CRYPTO:20"], ["업종·테마", "bull:kind:theme:20"]]
    .map(([l, k]) => { const v = s[k]; return v && v.n ? row([`<b>${l}</b>`, fmt.n(v.n), `<span class="${v.mean > 0 ? "pos-v" : "neg-v"}">${fmt.pct1(v.mean)}</span>`, fmt.pct0(v.win_rate), fmt.pct1(v.excess_mean), v.vol_ratio_median ? v.vol_ratio_median + "배" : "—"]) : row([l, "—", "—", "—", "—", "—"]); }).join("");
  const ta = $("#tbl-assets tbody");
  if (ta) ta.innerHTML = (d.top_assets_20 || []).slice(0, 10).map((a) => row([`<b>${a.name}</b> <span class="note">${a.market}</span>`, fmt.n(a.n), `<span class="${a.mean > 0 ? "pos-v" : "neg-v"}">${fmt.pct1(a.mean)}</span>`, fmt.pct0(a.win_rate), a.vol_ratio_median ? a.vol_ratio_median + "배" : "—"])).join("");
  const rk = d.channel_ranking || {};
  const rrow = (r, i) => `<div class="r"><i>${i + 1}</i><span><b>${r.title}</b><small>n=${fmt.n(r.n)} · 평균 ${fmt.pct1(r.mean)} · 상승 ${fmt.pct0(r.win_rate)}</small></span><span class="v ${r.excess_mean >= 0 ? "pos-v" : "neg-v"}">${fmt.pct1(r.excess_mean)}</span></div>`;
  if ($("#rank-top")) { $("#rank-top").className = "ranks top"; $("#rank-top").innerHTML = (rk.top || []).map(rrow).join(""); }
  if ($("#rank-bottom")) { $("#rank-bottom").className = "ranks bottom"; $("#rank-bottom").innerHTML = (rk.bottom || []).map(rrow).join(""); }
  const tt = $("#tbl-themes tbody");
  if (tt) tt.innerHTML = (d.top_themes_20 || []).slice(0, 8).map((a) => row([`<b>${a.name}</b>`, fmt.n(a.n), `<span class="${a.mean > 0 ? "pos-v" : "neg-v"}">${fmt.pct1(a.mean)}</span>`, fmt.pct0(a.win_rate)])).join("");
  const tr = $("#tbl-trend tbody");
  if (tr) tr.innerHTML = (d.trending_30d || []).slice(0, 8).map((t) => row([`<b>${t.name}</b>`, fmt.n(t.mentions), fmt.n(t.prev), t.channels])).join("");
}
function renderFindings(d) {
  const s = d.summary || {}; const o = s["bull:overall:20"] || s["overall:20"], o5 = s["bull:overall:5"] || s["overall:5"], o60 = s["bull:overall:60"] || s["overall:60"]; const th = s["bull:kind:theme:20"] || s["kind:theme:20"];
  const f = {};
  if (o && o.n) f[1] = `"오른다"고 한 언급 뒤 20거래일 평균 <b>${fmt.pct1(o.mean)}</b>, 상승 확률 <b>${fmt.pct0(o.win_rate)}</b> (n=${fmt.n(o.n)}). ${o.win_rate >= 0.45 && o.win_rate <= 0.55 ? "동전 던지기와 같다. 언급은 방향 정보가 아니다." : o.win_rate > 0.55 ? "오른 쪽이 많았다. 시장 효과는 다음 줄에서." : "내린 쪽이 많았다. 언급이 몰릴 땐 이미 오른 뒤였다."}`;
  if (o && o.excess_mean != null) f[2] = `시장을 빼면 <b>${fmt.pct1(o.excess_mean)}</b>, 시장을 이긴 비율 <b>${fmt.pct0(o.excess_win_rate)}</b>. ${Math.abs(o.excess_mean) < 0.01 ? "오른 건 시장 덕이었다." : o.excess_mean > 0 ? "시장보다 조금 더 올랐다." : "언급 뒤에 사면 시장을 못 따라갔다."}`;
  if (o && o.vol_ratio_median) f[3] = o.vol_ratio_median < 1
    ? `거래량은 언급 <b>앞</b>이 더 많았다 (언급 뒤 5일 ÷ 앞 20일 = <b>${o.vol_ratio_median}배</b>, 늘어난 언급 <b>${fmt.pct0(o.vol_up_rate)}</b>). 관심이 먼저, 유튜브는 뒤따른다.`
    : `언급 뒤 거래량이 <b>${o.vol_ratio_median}배</b>로 늘었다 (늘어난 언급 <b>${fmt.pct0(o.vol_up_rate)}</b>). 가격과 별개로 관심은 움직였다.`;
  if (o5 && o60 && o5.n && o60.n) f[4] = `5일 ${fmt.pct1(o5.mean)} → 20일 ${fmt.pct1(o.mean)} → 60일 ${fmt.pct1(o60.mean)}${th && th.n ? `. 종목 없이 업종만 말한 언급(${fmt.n(th.n)}건)은 20일 ${fmt.pct1(th.mean)}, 상승 ${fmt.pct0(th.win_rate)} — 종목 언급보다 ${th.win_rate > o.win_rate + 0.03 ? "자주 올랐다" : th.win_rate < o.win_rate - 0.03 ? "덜 올랐다" : "비슷했다"}` : ""}.`;
  const kr = s["bull:market:KRX:20"] || s["market:KRX:20"];
  if (kr && kr.disclosure_n) f[5] = `국내 언급 ${fmt.n(kr.disclosure_n)}건 중 <b>${fmt.pct0(kr.disclosure_rate)}</b>는 사건일 ±3일에 DART 주요 공시가 있었다. ${kr.disclosure_rate >= 0.3 ? "언급의 상당수는 공시를 뒤따른 해설이다." : "대부분은 공시와 무관했다. 수급·테마가 언급을 만든다."}`;
  Object.entries(f).forEach(([k, v]) => { const el = $(`[data-finding="${k}"]`); if (el) el.innerHTML = v; });
}

// ── 스냅샷 → 실시간 ──
async function loadSnapshot() {
  try { const r = await fetch("data/snapshot.json", { cache: "no-store" }); if (r.ok) bind(derive(await r.json())); } catch (e) { /* 없으면 정적 숫자 유지 */ }
}
async function loadLive() {
  const api = CONFIG.api; const j = async (p) => (await fetch(api + p, { signal: AbortSignal.timeout(8000) })).json();
  try {
    const [yt, me, mk, st, ch, sums, rk] = await Promise.all([j("/youtube/v1/coverage"), j("/mentions/v1/coverage"), j("/market-data/v1/coverage"), j("/stats/v1/coverage"), j("/youtube/v1/channels"), j("/stats/v1/summaries?slim=true"), j("/stats/v1/channels/ranking?horizon=20&limit=3")]);
    const summary = Object.fromEntries(sums.items.map((i) => [i.key, i.value]));
    if (window.__snap?.summary) Object.keys(window.__snap.summary).forEach((k) => { if (summary[k] && !summary[k].histogram && window.__snap.summary[k]) summary[k].histogram = window.__snap.summary[k].histogram; });
    const chm = Object.fromEntries(ch.items.map((c) => [c.channel_id, c]));
    const channel_ranking = Object.fromEntries(["top", "bottom"].map((side) => [side, rk[side].map((r) => ({ ...r, title: chm[r.channel_id]?.title || r.channel_id }))]));
    const d = derive({ youtube: yt, mentions: me, market: mk, stats: st, summary,
      channels: { total: ch.items.length, stock: ch.items.filter((c) => c.category === "stock").length, crypto: ch.items.filter((c) => c.category === "crypto").length },
      generated_at: "실시간", top_assets_20: window.__snap?.top_assets_20, top_themes_20: window.__snap?.top_themes_20, trending_30d: window.__snap?.trending_30d, channel_ranking });
    bind(d);
    $$(".live").forEach((e) => { e.classList.add("on"); e.querySelector("span").textContent = "실시간 · " + api.replace(/^https?:\/\//, ""); });
  } catch (e) { /* Render 가 자고 있으면 스냅샷 유지 */ }
}
(async () => {
  try { const r = await fetch("data/snapshot.json", { cache: "no-store" }); if (r.ok) { window.__snap = await r.json(); bind(derive(window.__snap)); } } catch (e) {}
  if (location.hostname !== "localhost" && location.hostname !== "127.0.0.1") loadLive(); else if (new URLSearchParams(location.search).has("live")) loadLive();
})();

// ── 슬라이드 모드: 한 화면에 한 장, ← → 로 넘긴다. ?scroll 이면 옛 스크롤 모드 ──
const STATIC = new URLSearchParams(location.search).has("static");
const SCROLL = new URLSearchParams(location.search).has("scroll");
const slides = $$(".slide");
let cur = 0;
function reveal(el) { $$(".rv", el).forEach((x) => x.classList.add("on")); }
function show(i, push = true) {
  cur = Math.max(0, Math.min(slides.length - 1, i));
  slides.forEach((s, k) => s.classList.toggle("active", k === cur));
  reveal(slides[cur]);
  slides[cur].scrollTop = 0;
  $("#pos").textContent = `${cur + 1} / ${slides.length}`;
  $("#progress").style.width = `${((cur + 1) / slides.length) * 100}%`;
  $$(".dots button").forEach((b, k) => b.classList.toggle("on", k === cur));
  if (push) history.replaceState(null, "", `#${cur + 1}`);
}
if (!SCROLL) {
  document.documentElement.classList.add("deck-mode");
  const dots = document.createElement("div"); dots.className = "dots";
  slides.forEach((s, k) => { const b = document.createElement("button"); b.title = s.querySelector("h1,h2")?.textContent?.slice(0, 30) || `${k + 1}`; b.onclick = () => show(k); dots.appendChild(b); });
  document.body.appendChild(dots);
  const hint = document.createElement("div"); hint.className = "navhint"; hint.innerHTML = '<span class="kbd">←</span><span class="kbd">→</span> 넘기기 · <span class="kbd">Home</span> 처음';
  document.body.appendChild(hint);
  const fromHash = parseInt((location.hash || "#1").slice(1), 10);
  const byId = location.hash && location.hash.length > 3 ? slides.findIndex((s) => "#" + s.id === location.hash) : -1;
  show(byId >= 0 ? byId : (isNaN(fromHash) ? 0 : fromHash - 1), false);
  if (STATIC) $$(".rv").forEach((x) => x.classList.add("on"));
  window.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
    if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(e.key)) { e.preventDefault(); show(cur + 1); }
    if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(e.key)) { e.preventDefault(); show(cur - 1); }
    if (e.key === "Home") show(0);
    if (e.key === "End") show(slides.length - 1);
  });
  let touchX = null;
  window.addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; }, { passive: true });
  window.addEventListener("touchend", (e) => { if (touchX == null) return; const dx = e.changedTouches[0].clientX - touchX; if (Math.abs(dx) > 60) show(cur + (dx < 0 ? 1 : -1)); touchX = null; });
  window.addEventListener("hashchange", () => { const n = parseInt(location.hash.slice(1), 10); if (!isNaN(n) && n - 1 !== cur) show(n - 1, false); });
} else {
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) reveal(e.target); }), { threshold: 0.18 });
  slides.forEach((s) => io.observe(s));
  setTimeout(() => $$(".rv").forEach((x) => x.classList.add("on")), 1000);
  function current() { const y = window.scrollY + window.innerHeight / 2; let i = 0; slides.forEach((s, k) => { if (s.offsetTop <= y) i = k; }); return i; }
  function update() { const i = current(); $("#pos").textContent = `${i + 1} / ${slides.length}`; $("#progress").style.width = `${((i + 1) / slides.length) * 100}%`; }
  window.addEventListener("scroll", update, { passive: true }); update();
}

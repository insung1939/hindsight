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
    const v = s[`overall:${h}`];
    if (!v || !v.n) return card(`${h}거래일 뒤`, "—", "표본 없음");
    const cls = v.mean > 0 ? "pos-v" : v.mean < 0 ? "neg-v" : "";
    return card(`${h}거래일 뒤 · 표본 ${fmt.n(v.n)}건${v.low_sample ? " (참고용)" : ""}`,
      `${fmt.pct1(v.mean)}<small>평균</small>`,
      `중앙값 ${fmt.pct1(v.median)} · 상승 확률 <b>${fmt.pct0(v.win_rate)}</b> · 벤치마크 대비 <b>${fmt.pct1(v.excess_mean)}</b>` +
      (v.vol_ratio_median ? ` · 거래량 <b>${v.vol_ratio_median}배</b>` : ""), cls);
  }).join("");
}
function renderHist(d) {
  const el = $("#hist-overall"); if (!el) return;
  const v = (d.summary || {})["overall:20"]; if (!v || !v.histogram) return;
  const max = Math.max(1, ...v.histogram.map((b) => b.n));
  const label = (b) => (b.from <= -1 ? "< −20%" : b.to >= 9 ? "> +20%" : `${Math.round(b.from * 100)}~${Math.round(b.to * 100)}%`);
  el.innerHTML = v.histogram.map((b) => `<div class="c"><div class="n">${fmt.n(b.n)}</div><div class="b ${b.from >= 0 ? "up" : ""}" style="height:${(b.n / max) * 100}%"></div><div class="l">${label(b)}</div></div>`).join("");
}
function row(cells) { return `<tr>${cells.map((c, i) => `<td class="${i ? "r" : ""}">${c}</td>`).join("")}</tr>`; }
function renderTables(d) {
  const s = d.summary || {};
  const tm = $("#tbl-market tbody");
  if (tm) tm.innerHTML = [["종목·코인 전체", "overall:20"], ["국내 주식", "market:KRX:20"], ["미국 주식", "market:US:20"], ["코인", "market:CRYPTO:20"], ["업종·테마 (ETF)", "kind:theme:20"]]
    .map(([l, k]) => { const v = s[k]; return v && v.n ? row([`<b>${l}</b>`, fmt.n(v.n), `<span class="${v.mean > 0 ? "pos-v" : "neg-v"}">${fmt.pct1(v.mean)}</span>`, fmt.pct0(v.win_rate), fmt.pct1(v.excess_mean), v.vol_ratio_median ? v.vol_ratio_median + "배" : "—"]) : row([l, "—", "—", "—", "—", "—"]); }).join("");
  const ta = $("#tbl-assets tbody");
  if (ta) ta.innerHTML = (d.top_assets_20 || []).slice(0, 10).map((a) => row([`<b>${a.name}</b> <span class="note">${a.market}</span>`, fmt.n(a.n), `<span class="${a.mean > 0 ? "pos-v" : "neg-v"}">${fmt.pct1(a.mean)}</span>`, fmt.pct0(a.win_rate), a.vol_ratio_median ? a.vol_ratio_median + "배" : "—"])).join("");
  const tt = $("#tbl-themes tbody");
  if (tt) tt.innerHTML = (d.top_themes_20 || []).slice(0, 8).map((a) => row([`<b>${a.name}</b>`, fmt.n(a.n), `<span class="${a.mean > 0 ? "pos-v" : "neg-v"}">${fmt.pct1(a.mean)}</span>`, fmt.pct0(a.win_rate)])).join("");
  const tr = $("#tbl-trend tbody");
  if (tr) tr.innerHTML = (d.trending_30d || []).slice(0, 8).map((t) => row([`<b>${t.name}</b>`, fmt.n(t.mentions), fmt.n(t.prev), t.channels])).join("");
}
function renderFindings(d) {
  const s = d.summary || {}; const o = s["overall:20"], o5 = s["overall:5"], o60 = s["overall:60"]; const th = s["kind:theme:20"];
  const f = {};
  if (o && o.n) f[1] = `언급 뒤 20거래일 평균 수익률은 <b>${fmt.pct1(o.mean)}</b>, 상승 확률은 <b>${fmt.pct0(o.win_rate)}</b>였다(표본 ${fmt.n(o.n)}건). ${o.win_rate >= 0.45 && o.win_rate <= 0.55 ? "동전 던지기와 다르지 않다 — 언급은 방향 정보가 아니다." : o.win_rate > 0.55 ? "오른 경우가 더 많았다. 다만 시장 전체가 오른 기간인지 초과수익으로 확인해야 한다." : "내린 경우가 더 많았다. 언급이 몰리는 시점은 이미 오른 뒤일 가능성을 시사한다."}`;
  if (o && o.excess_mean != null) f[2] = `같은 기간 벤치마크(코스피·S&P500·비트코인)를 빼면 초과수익은 <b>${fmt.pct1(o.excess_mean)}</b>, 시장을 이긴 비율은 <b>${fmt.pct0(o.excess_win_rate)}</b>. ${Math.abs(o.excess_mean) < 0.01 ? "종목이 오른 건 대체로 시장이 오른 덕이었다." : o.excess_mean > 0 ? "시장보다 조금 더 올랐다." : "시장보다 덜 올랐다 — 언급 뒤에 사면 평균적으로 시장을 못 따라갔다."}`;
  if (o && o.vol_ratio_median) f[3] = o.vol_ratio_median < 1
    ? `거래량은 언급 <b>뒤</b>보다 <b>앞</b>이 더 많았다. 언급 뒤 5거래일 거래량은 언급 전 20일 평균의 <b>${o.vol_ratio_median}배</b>(중앙값), 거래량이 늘어난 언급은 <b>${fmt.pct0(o.vol_up_rate)}</b>뿐. 관심이 먼저 몰리고 유튜브가 뒤따른다는 뜻이다.`
    : `가격과 별개로 <b>관심은 분명히 움직였다</b>. 언급 뒤 5거래일 거래량은 언급 전 20일 평균의 <b>${o.vol_ratio_median}배</b>(중앙값), 거래량이 늘어난 언급이 <b>${fmt.pct0(o.vol_up_rate)}</b>였다.`;
  if (o5 && o60 && o5.n && o60.n) f[4] = `기간을 늘릴수록 평균은 5일 ${fmt.pct1(o5.mean)} → 20일 ${fmt.pct1(o.mean)} → 60일 ${fmt.pct1(o60.mean)}로 움직였다${th && th.n ? `. 종목 없이 "반도체·코스피"만 말한 업종 언급(${fmt.n(th.n)}건)은 20일 뒤 ${fmt.pct1(th.mean)}, 상승 확률 ${fmt.pct0(th.win_rate)}로 종목 언급과 ${Math.abs(th.win_rate - o.win_rate) < 0.05 ? "비슷했다" : th.win_rate > o.win_rate ? "달리 더 자주 올랐다" : "달리 덜 올랐다"}` : ""}.`;
  const kr = s["market:KRX:20"];
  if (kr && kr.disclosure_n) f[5] = `국내 종목 언급 ${fmt.n(kr.disclosure_n)}건 중 <b>${fmt.pct0(kr.disclosure_rate)}</b>는 사건일 ±3일 안에 DART 주요 공시(실적·계약·자금조달·주요사항)가 있었다. ${kr.disclosure_rate >= 0.3 ? "유튜브 언급의 상당수는 공시라는 공개 정보를 뒤따라 나온 해설이다." : "대부분의 언급은 공시와 무관하게 나왔다 — 공시 외의 재료(수급·테마)가 언급을 만든다."}`;
  Object.entries(f).forEach(([k, v]) => { const el = $(`[data-finding="${k}"]`); if (el) el.innerHTML = v; });
}

// ── 스냅샷 → 실시간 ──
async function loadSnapshot() {
  try { const r = await fetch("data/snapshot.json", { cache: "no-store" }); if (r.ok) bind(derive(await r.json())); } catch (e) { /* 없으면 정적 숫자 유지 */ }
}
async function loadLive() {
  const api = CONFIG.api; const j = async (p) => (await fetch(api + p, { signal: AbortSignal.timeout(8000) })).json();
  try {
    const [yt, me, mk, st, ch, sums] = await Promise.all([j("/youtube/v1/coverage"), j("/mentions/v1/coverage"), j("/market-data/v1/coverage"), j("/stats/v1/coverage"), j("/youtube/v1/channels"), j("/stats/v1/summaries")]);
    const summary = Object.fromEntries(sums.items.map((i) => [i.key, i.value]));
    const d = derive({ youtube: yt, mentions: me, market: mk, stats: st, summary,
      channels: { total: ch.items.length, stock: ch.items.filter((c) => c.category === "stock").length, crypto: ch.items.filter((c) => c.category === "crypto").length },
      generated_at: "실시간", top_assets_20: window.__snap?.top_assets_20, top_themes_20: window.__snap?.top_themes_20, trending_30d: window.__snap?.trending_30d });
    bind(d);
    $$(".live").forEach((e) => { e.classList.add("on"); e.querySelector("span").textContent = "실시간 · " + api.replace(/^https?:\/\//, ""); });
  } catch (e) { /* Render 가 자고 있으면 스냅샷 유지 */ }
}
(async () => {
  try { const r = await fetch("data/snapshot.json", { cache: "no-store" }); if (r.ok) { window.__snap = await r.json(); bind(derive(window.__snap)); } } catch (e) {}
  if (location.hostname !== "localhost" && location.hostname !== "127.0.0.1") loadLive(); else if (new URLSearchParams(location.search).has("live")) loadLive();
})();

// ── 등장 애니메이션 · 진행 · 키보드 ──
const STATIC = new URLSearchParams(location.search).has("static");  // ?static : 애니메이션·부드러운 스크롤 끄기 (인쇄·스크린샷용)
if (STATIC) { document.documentElement.style.scrollBehavior = "auto"; $$(".rv").forEach((x) => x.classList.add("on")); }
const slides = $$(".slide");
const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { $$(".rv", e.target).forEach((x) => x.classList.add("on")); } }), { threshold: 0.18 });
slides.forEach((s) => io.observe(s));
// 백그라운드 탭·인쇄·구형 브라우저 대비: 1초 뒤에는 무조건 다 보이게 (애니메이션은 덤이지 조건이 아니다)
setTimeout(() => $$(".rv").forEach((x) => x.classList.add("on")), 1000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) $$(".rv").forEach((x) => x.classList.add("on")); });
if (location.hash) setTimeout(() => $(location.hash)?.scrollIntoView({ behavior: STATIC ? "auto" : "smooth" }), STATIC ? 0 : 50);
function current() { const y = window.scrollY + window.innerHeight / 2; let i = 0; slides.forEach((s, k) => { if (s.offsetTop <= y) i = k; }); return i; }
function update() { const i = current(); $("#pos").textContent = `${i + 1} / ${slides.length}`; $("#progress").style.width = `${((i + 1) / slides.length) * 100}%`; }
window.addEventListener("scroll", update, { passive: true }); update();
window.addEventListener("keydown", (e) => {
  if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
  const i = current();
  if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(e.key)) { e.preventDefault(); slides[Math.min(i + 1, slides.length - 1)].scrollIntoView({ behavior: "smooth" }); }
  if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) { e.preventDefault(); slides[Math.max(i - 1, 0)].scrollIntoView({ behavior: "smooth" }); }
  if (e.key === "Home") slides[0].scrollIntoView({ behavior: "smooth" });
  if (e.key === "End") slides[slides.length - 1].scrollIntoView({ behavior: "smooth" });
});

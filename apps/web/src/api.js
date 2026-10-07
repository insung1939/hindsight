// 서비스별 주소. 배포는 합본 API 하나(VITE_API_URL, .env.production)에 서비스 접두사를 붙인다.
// 서비스별 주소(VITE_STATS_URL …)를 주면 그게 우선이라 분리 실행(로컬 8001~8004, 세미나)도 그대로 된다.
const env = import.meta.env;
const gw = (env.VITE_API_URL || "").replace(/\/$/, "");
export const URLS = {
  stats: env.VITE_STATS_URL || (gw ? gw + "/stats" : "http://localhost:8004"),
  mentions: env.VITE_MENTIONS_URL || (gw ? gw + "/mentions" : "http://localhost:8003"),
  marketData: env.VITE_MARKET_DATA_URL || (gw ? gw + "/market-data" : "http://localhost:8001"),
  youtube: env.VITE_YOUTUBE_URL || (gw ? gw + "/youtube" : "http://localhost:8002"),
};
export const API_BASE = gw || "http://localhost:8000";

export class ApiError extends Error {
  constructor(problem, status) {
    super(problem?.detail || problem?.title || `HTTP ${status}`);
    this.problem = problem;
    this.status = status;
  }
}

// Render 무료 플랜은 15분 쉬면 잠들고, 재배포 중엔 잠깐 502 가 난다. 네트워크 오류·502·503·504 는 최대 4번(약 40초) 다시 시도한다.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const listeners = new Set();
export const onWaking = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };
const notify = (state) => listeners.forEach((fn) => fn(state));
// 진행 중 요청 수 — 상단 로딩 바가 본다
let pending = 0;
const progressListeners = new Set();
export const onProgress = (fn) => { progressListeners.add(fn); return () => progressListeners.delete(fn); };
const bump = (d) => { pending = Math.max(0, pending + d); progressListeners.forEach((fn) => fn(pending)); };
const cache = new Map(); // 같은 세션 안에서 같은 GET 은 한 번만 (사전·채널·요약처럼 큰 응답)

export async function api(service, path, { method = "GET", body, params, ttl = 0 } = {}) {
  const url = new URL(URLS[service] + path);
  if (params) Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const key = method === "GET" && ttl ? url.toString() : null;
  if (key && cache.has(key) && cache.get(key).exp > Date.now()) return cache.get(key).data;
  const init = { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined };
  let lastErr = null;
  bump(1);
  try {
  for (let attempt = 0; attempt < 5; attempt++) {
    if (attempt) { notify({ waking: true, attempt }); await sleep(attempt * 5000); }
    let res;
    try {
      res = await fetch(url, init);
    } catch (e) { lastErr = Object.assign(new ApiError({ detail: "서버에 연결하지 못했습니다. 잠든 서버를 깨우는 중일 수 있습니다." }, 0), { cause: e }); continue; }
    if ([502, 503, 504].includes(res.status)) { lastErr = new ApiError({ detail: `서버가 깨어나는 중입니다 (HTTP ${res.status})` }, res.status); continue; }
    notify({ waking: false });
    const requestId = res.headers.get("X-Request-ID");
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) throw Object.assign(new ApiError(data, res.status), { requestId });
    if (key) cache.set(key, { data, exp: Date.now() + ttl });
    return data;
  }
  notify({ waking: false, failed: true });
  throw lastErr;
  } finally { bump(-1); }
}

export const pct = (x, d = 1) => (x == null ? "—" : ((x > 0 ? "+" : "") + (x * 100).toFixed(d) + "%"));
export const pct0 = (x) => (x == null ? "—" : Math.round(x * 100) + "%");
export const num = (n) => (n == null ? "—" : Number(n).toLocaleString("ko-KR"));
export const dateOnly = (s) => (s || "").slice(0, 10);
export const compact = (n) => (n == null ? "—" : n >= 1e8 ? (n / 1e8).toFixed(1) + "억" : n >= 1e4 ? Math.round(n / 1e4).toLocaleString("ko-KR") + "만" : num(n));
export const sign = (x) => (x > 0 ? "pos" : x < 0 ? "neg" : "");

// 종목 이름 캐시 — market-data 사전을 한 번 받아 asset_id → 자산
export async function assetNames(all = false) {
  const d = await api("marketData", "/v1/assets/names", { params: all ? { all: true } : undefined, ttl: 10 * 60e3 });
  return Object.fromEntries(d.items.map((a) => [a.asset_id, a]));
}
// 종목별 요약(한 기간, 히스토그램 없이) — asset_id → value
export async function assetSummaries(horizon) {
  const s = await api("stats", "/v1/summaries", { params: { prefix: "asset:", horizon, slim: true }, ttl: 5 * 60e3 });
  const suf = `:${horizon}`;
  return Object.fromEntries(s.items.map((i) => [i.key.slice(6, -suf.length), i.value]));
}
// 채널 캐시 — channel_id → {title, handle, anon_code, category, subscriber_count}
export async function channelMap() {
  const d = await api("youtube", "/v1/channels", { ttl: 10 * 60e3 });
  return Object.fromEntries(d.items.map((c) => [c.channel_id, c]));
}
export const MARKET_LABEL = { KRX: "국내", US: "미국", CRYPTO: "코인", INDEX: "지수" };
export const HORIZON_LABEL = { 5: "5거래일 (약 1주)", 20: "20거래일 (약 1개월)", 60: "60거래일 (약 3개월)" };

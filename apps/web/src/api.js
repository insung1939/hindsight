// 서비스별 주소. 화면은 stats · mentions 를 주로 부르고, market-data 는 종목 이름·시세(타임라인) 읽기, youtube 는 수집 현황만.
// 배포는 합본 API 하나(VITE_API_URL, .env.production)에 서비스 접두사를 붙인다.
// 서비스별 주소(VITE_STATS_URL …)를 주면 그게 우선이라 분리 실행(로컬 8001~8004, 세미나)도 그대로 된다.
const env = import.meta.env;
const gw = (env.VITE_API_URL || "").replace(/\/$/, "");
export const URLS = {
  stats: env.VITE_STATS_URL || (gw ? gw + "/stats" : "http://localhost:8004"),
  mentions: env.VITE_MENTIONS_URL || (gw ? gw + "/mentions" : "http://localhost:8003"),
  marketData: env.VITE_MARKET_DATA_URL || (gw ? gw + "/market-data" : "http://localhost:8001"),
  youtube: env.VITE_YOUTUBE_URL || (gw ? gw + "/youtube" : "http://localhost:8002"),
};

export class ApiError extends Error {
  constructor(problem, status) {
    super(problem?.detail || problem?.title || `HTTP ${status}`);
    this.problem = problem;
    this.status = status;
  }
}

// RFC 9457 problem+json 을 그대로 오류 객체로 올린다. X-Request-ID 는 응답 헤더에서 읽어 디버깅에 쓴다.
// Render 무료 플랜은 15분 쉬면 잠들고, 재배포 중엔 잠깐 502 가 난다. 네트워크 오류·502·503·504 는 최대 4번(약 40초) 다시 시도한다.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const listeners = new Set();
export const onWaking = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };
const notify = (state) => listeners.forEach((fn) => fn(state));

export async function api(service, path, { method = "GET", body, params } = {}) {
  const url = new URL(URLS[service] + path);
  if (params) Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const init = { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined };
  let lastErr = null;
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
    return data;
  }
  notify({ waking: false, failed: true });
  throw lastErr;
}

export const pct = (x, d = 1) => (x == null ? "—" : ((x > 0 ? "+" : "") + (x * 100).toFixed(d) + "%"));
export const num = (n) => (n ?? 0).toLocaleString("ko-KR");
export const dateOnly = (s) => (s || "").slice(0, 10);

// 종목 이름 캐시 — market-data 사전을 한 번 받아 asset_id → 이름
let _names = null;
export async function assetNames() {
  if (_names) return _names;
  const d = await api("marketData", "/v1/assets", { params: { limit: 5000 } });
  _names = Object.fromEntries(d.items.map((a) => [a.asset_id, a]));
  return _names;
}

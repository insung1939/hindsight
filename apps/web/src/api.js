// 서비스별 주소. 화면은 stats · mentions 를 주로 부르고, market-data 는 종목 이름·시세(타임라인) 읽기, youtube 는 수집 현황만.
// 배포는 합본 게이트웨이 하나(VITE_API_URL, 예: https://hindsight-api.onrender.com)에 접두사로 붙인다.
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
export async function api(service, path, { method = "GET", body, params } = {}) {
  const url = new URL(URLS[service] + path);
  if (params) Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const requestId = res.headers.get("X-Request-ID");
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw Object.assign(new ApiError(data, res.status), { requestId });
  return data;
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

// 서비스별 주소. 프론트는 plan · portfolio · backtest · income 을 부르고, market-data 는 '데이터' 페이지에서 읽기만 한다.
const env = import.meta.env;
export const URLS = {
  plan: env.VITE_PLAN_URL || "http://localhost:8004",
  portfolio: env.VITE_PORTFOLIO_URL || "http://localhost:8003",
  backtest: env.VITE_BACKTEST_URL || "http://localhost:8005",
  income: env.VITE_INCOME_URL || "http://localhost:8002",
  marketData: env.VITE_MARKET_DATA_URL || "http://localhost:8001",
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

export const krw = (n) => Math.round(n ?? 0).toLocaleString("ko-KR") + "원";
export const pct = (x, d = 1) => ((x ?? 0) * 100).toFixed(d) + "%";

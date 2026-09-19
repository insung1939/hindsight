import { useEffect, useState } from "react";
import { api, krw } from "../api";

function LineChart({ series }) {
  if (!series?.length) return null;
  const W = 800, H = 200, P = 8;
  const max = Math.max(...series.map((s) => Math.max(s.value_krw, s.invested_krw)));
  const x = (i) => P + (i / (series.length - 1)) * (W - 2 * P);
  const y = (v) => H - P - (v / max) * (H - 2 * P);
  const path = (key) => series.map((s, i) => `${i ? "L" : "M"}${x(i)},${y(s[key])}`).join(" ");
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <path d={path("invested_krw")} fill="none" stroke="currentColor" strokeOpacity=".35" strokeWidth="2" />
      <path d={path("value_krw")} fill="none" stroke="var(--brand)" strokeWidth="2.5" />
    </svg>
  );
}

export default function TimeMachine({ portfolio }) {
  const [rules, setRules] = useState([]);
  const [amount, setAmount] = useState(portfolio.monthly_budget || 1000000);
  const [start, setStart] = useState("2021-04-01");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => { api("portfolio", `/v1/portfolios/${portfolio.id}/rules`).then((r) => setRules(r.items)).catch(setErr); }, [portfolio.id]);

  const run = async () => {
    setBusy(true); setErr(null);
    try {
      const weights = Object.fromEntries(rules.map((r) => [r.asset_id, r.target_weight]));
      const r = await api("backtest", "/v1/runs", { method: "POST", body: { weights, monthly_amount_krw: Number(amount), start, buy_day: portfolio.buy_day } });
      setRes(r.result);
    } catch (e) { setErr(e); } finally { setBusy(false); }
  };

  return (
    <div className="grid">
      <div className="card wide">
        <h3>내 규칙으로 과거에 했다면 — {rules.map((r) => `${r.asset_id} ${Math.round(r.target_weight * 100)}%`).join(" · ")}</h3>
        <div className="row">
          <label>월 적립액</label><input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
          <label>시작일</label><input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          <button className="primary" onClick={run} disabled={busy || !rules.length}>{busy ? "계산 중…" : "돌려보기"}</button>
        </div>
        {err && <div className="problem">{err.message}</div>}
      </div>
      {res && (<>
        <div className="card"><h3>투입</h3><div className="big">{krw(res.invested_krw)}</div><p className="muted">{res.months}개월</p></div>
        <div className="card"><h3>평가</h3><div className="big">{krw(res.final_value_krw)}</div>
          <p className={res.return_pct >= 0 ? "good" : "bad"}>수익률 {res.return_pct}%</p></div>
        <div className="card"><h3>최대 낙폭</h3><div className="big bad">{res.max_drawdown_pct}%</div>
          <p className="muted">이만큼 빠져도 계속 살 수 있어야 적립식이 완성됩니다.</p></div>
        <div className="card wide">
          <h3>평가액(진한 선) vs 투입액(연한 선)</h3>
          <LineChart series={res.series} />
          {res.warnings?.length > 0 && <p className="warn" style={{ fontSize: 13 }}>{res.warnings[0]}</p>}
        </div>
      </>)}
    </div>
  );
}

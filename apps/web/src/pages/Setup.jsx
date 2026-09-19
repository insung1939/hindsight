import { useState } from "react";
import { api } from "../api";

// 첫 사용자: 포트폴리오·계좌·규칙을 한 번에 만든다 (프로토타입용 빠른 시작).
const PRESET = [
  { asset_id: "US:SPY", label: "S&P500 (SPY)", weight: 0.4, account: "general" },
  { asset_id: "US:QQQ", label: "나스닥100 (QQQ)", weight: 0.3, account: "general" },
  { asset_id: "CRYPTO:KRW-BTC", label: "비트코인 (업비트)", weight: 0.3, account: "exchange" },
];

export default function Setup({ onDone }) {
  const [owner, setOwner] = useState("");
  const [budget, setBudget] = useState(1000000);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const create = async () => {
    setBusy(true); setErr(null);
    try {
      const pf = await api("portfolio", "/v1/portfolios", { method: "POST", body: { owner, name: `${owner}의 적립`, monthly_budget: Number(budget), buy_day: 5 } });
      const gen = await api("portfolio", `/v1/portfolios/${pf.id}/accounts`, { method: "POST", body: { name: "증권사 일반", account_type: "general" } });
      const ex = await api("portfolio", `/v1/portfolios/${pf.id}/accounts`, { method: "POST", body: { name: "거래소", account_type: "exchange" } });
      for (const p of PRESET) {
        await api("portfolio", `/v1/portfolios/${pf.id}/rules`, { method: "POST", body: { account_id: p.account === "general" ? gen.id : ex.id, asset_id: p.asset_id, target_weight: p.weight } });
      }
      onDone();
    } catch (e) { setErr(e); } finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ marginTop: 20 }}>
      <h2>시작하기</h2>
      <p className="muted">이름과 월 적립액만 넣으면 기본 규칙(SPY 40 · QQQ 30 · BTC 30)으로 포트폴리오를 만듭니다. 규칙은 나중에 API 로 바꿀 수 있습니다.</p>
      <div className="row">
        <label>이름</label><input value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="insung" />
        <label>월 적립액(원)</label><input type="number" value={budget} onChange={(e) => setBudget(e.target.value)} />
        <button className="primary" disabled={!owner || busy} onClick={create}>{busy ? "만드는 중…" : "만들기"}</button>
      </div>
      {err && <div className="problem">{err.message}</div>}
    </div>
  );
}

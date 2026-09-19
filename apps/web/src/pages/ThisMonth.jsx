import { useEffect, useState } from "react";
import { api, krw, pct } from "../api";

const month = new Date().toISOString().slice(0, 7);

export default function ThisMonth({ portfolio }) {
  const [ins, setIns] = useState(null);
  const [execs, setExecs] = useState([]);
  const [comp, setComp] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const load = async () => {
    try {
      const [i, e, c] = await Promise.all([
        api("plan", "/v1/instructions", { params: { portfolio_id: portfolio.id, month } }),
        api("portfolio", `/v1/portfolios/${portfolio.id}/executions`),
        api("portfolio", `/v1/portfolios/${portfolio.id}/compliance`, { params: { months: 12 } }),
      ]);
      setIns(i.items[0] ?? null); setExecs(e.items); setComp(c); setErr(null);
    } catch (e) { setErr(e); }
  };
  useEffect(() => { load(); }, [portfolio.id]);

  const generate = async () => {
    setBusy(true);
    try { await api("plan", "/v1/instructions", { method: "POST", body: { portfolio_id: portfolio.id, month } }); await load(); }
    catch (e) { setErr(e); } finally { setBusy(false); }
  };

  const record = async (item, status) => {
    try {
      await api("portfolio", `/v1/portfolios/${portfolio.id}/executions`, { method: "POST", body: {
        instruction_id: ins.id, asset_id: item.asset_id, executed_on: new Date().toISOString().slice(0, 10),
        status, amount_krw: status === "done" ? item.amount_krw : 0, quantity: status === "done" ? item.quantity : 0 } });
      await load();
    } catch (e) { setErr(e); }
  };
  const doneFor = (asset) => execs.find((e) => e.instruction_id === ins?.id && e.asset_id === asset);

  return (
    <div className="grid">
      <div className="card">
        <h3>{month} 적립 예산</h3>
        <div className="big">{krw(portfolio.monthly_budget)}</div>
        <p className="muted">매수일 매월 {portfolio.buy_day}일 · 목표 비중과 현재 비중 차이를 예산으로 메웁니다.</p>
        {!ins && <button className="primary" onClick={generate} disabled={busy}>{busy ? "계산 중…" : "이번 달 지시서 만들기"}</button>}
        {ins && <button className="ghost" onClick={generate} disabled={busy}>다시 계산</button>}
      </div>
      <div className="card">
        <h3>규칙 준수 (최근 12개월)</h3>
        {comp ? (<>
          <div className="big">{comp.score.toFixed(0)}점</div>
          <div className="bar"><i style={{ width: `${comp.score}%` }} /></div>
          <p className="muted">지시대로 {comp.done} · 건너뜀 {comp.skipped} · 임의 추가 {comp.extra} · 매도 {comp.sell} · 연속 {comp.streak_months}개월</p>
        </>) : <p className="muted">불러오는 중…</p>}
      </div>
      {err && <div className="card wide problem">{err.message}{err.requestId && <span className="muted"> · request {err.requestId}</span>}</div>}
      {ins && (
        <div className="card wide">
          <h3>매수 지시서 #{ins.id} · 평가액 {krw(ins.total_value_krw)}</h3>
          <table>
            <thead><tr><th>자산</th><th className="num">현재 → 목표</th><th className="num">매수 금액</th><th className="num">수량</th><th className="num">단가</th><th>실행</th></tr></thead>
            <tbody>
              {ins.items.map((it) => {
                const e = doneFor(it.asset_id);
                return (
                  <tr key={it.asset_id}>
                    <td>{it.asset_id}</td>
                    <td className="num">{pct(it.current_weight)} → {pct(it.target_weight, 0)}</td>
                    <td className="num"><b>{krw(it.amount_krw)}</b></td>
                    <td className="num">{it.quantity}</td>
                    <td className="num">{it.price.toLocaleString()} {it.currency}</td>
                    <td>
                      {e ? <span className={`pill ${e.status}`}>{e.status === "done" ? "실행함" : "건너뜀"}</span> : it.amount_krw > 0 ? (
                        <span className="row" style={{ margin: 0 }}>
                          <button className="primary" onClick={() => record(it, "done")}>샀다</button>
                          <button className="ghost" onClick={() => record(it, "skipped")}>건너뜀</button>
                        </span>
                      ) : <span className="muted">이번 달 없음</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

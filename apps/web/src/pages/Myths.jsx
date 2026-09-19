import { useState } from "react";
import { api } from "../api";

// 신화 검증 — "매수일이 결과를 바꾸는가". 환율 타이밍·커버드콜 원금잠식은 7주차에 추가.
export default function Myths() {
  const [asset, setAsset] = useState("US:SPY");
  const [start, setStart] = useState("2021-04-01");
  const [r, setR] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const run = async () => {
    setBusy(true); setErr(null);
    try { setR(await api("backtest", "/v1/analyses/purchase-day", { params: { asset_id: asset, start } })); }
    catch (e) { setErr(e); } finally { setBusy(false); }
  };

  return (
    <div className="grid">
      <div className="card wide">
        <h2>신화 1 · "매수일을 잘 고르면 수익이 다르다"</h2>
        <p className="muted">같은 자산에 매달 10만 원씩, 매수일만 1·5·10·15·20·25·28일로 바꿔 결과를 비교합니다.</p>
        <div className="row">
          <label>자산</label>
          <select value={asset} onChange={(e) => setAsset(e.target.value)}>
            <option>US:SPY</option><option>US:QQQ</option><option>CRYPTO:KRW-BTC</option>
          </select>
          <label>시작일</label><input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          <button className="primary" onClick={run} disabled={busy}>{busy ? "계산 중…" : "검증"}</button>
        </div>
        {err && <div className="problem">{err.message}</div>}
      </div>
      {r && (<>
        <div className="card wide">
          <table>
            <thead><tr>{r.by_day.map((d) => <th key={d.buy_day} className="num">{d.buy_day}일</th>)}</tr></thead>
            <tbody><tr>{r.by_day.map((d) => (
              <td key={d.buy_day} className={"num " + (d.buy_day === r.best_day ? "good" : d.buy_day === r.worst_day ? "bad" : "")}>{d.return_pct}%</td>
            ))}</tr></tbody>
          </table>
        </div>
        <div className="card wide">
          <h3>결론 · 최고 {r.best_day}일 / 최저 {r.worst_day}일 · 차이 {r.spread_pct}%p</h3>
          <p>{r.conclusion}</p>
          <p className="muted">표본: {r.start} ~ {r.end}. 기간이 짧으면 우연한 차이가 커 보입니다. 시작일을 앞당겨 다시 확인하세요.</p>
        </div>
      </>)}
      <div className="card"><h3>신화 2 · 환율 타이밍</h3><p className="muted">"달러가 쌀 때 사야 한다" — 7주차 추가 예정.</p></div>
      <div className="card"><h3>신화 3 · 커버드콜 분배금</h3><p className="muted">"월 분배금은 공짜 현금흐름이다" — 분배율 대비 기초지수 총수익 비교, 7주차 추가 예정.</p></div>
    </div>
  );
}

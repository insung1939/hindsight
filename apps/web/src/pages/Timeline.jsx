import { useEffect, useState } from "react";
import { api, assetNames, dateOnly, pct } from "../api";

// 종목 하나: 주가 선 위에 언급 시점을 점으로. 점을 누르면 그 언급의 5·20·60일 결과.
function Chart({ prices, events, onHover }) {
  if (!prices?.length) return <p className="muted">시세가 없습니다.</p>;
  const W = 900, H = 240, P = 10;
  const t = (d) => new Date(d).getTime();
  const xs = prices.map((p) => t(p.trade_date));
  const ys = prices.map((p) => p.close);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const X = (v) => P + ((v - x0) / (x1 - x0 || 1)) * (W - 2 * P);
  const Y = (v) => H - P - ((v - y0) / (y1 - y0 || 1)) * (H - 2 * P);
  const path = prices.map((p, i) => `${i ? "L" : "M"}${X(t(p.trade_date))},${Y(p.close)}`).join(" ");
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ height: 260 }}>
      <path d={path} fill="none" stroke="currentColor" strokeOpacity=".6" strokeWidth="1.5" />
      {events.filter((e) => e.t0_date).map((e) => (
        <circle key={e.mention_id} cx={X(t(e.t0_date))} cy={Y(e.t0_close)} r="6"
          fill={e.r20 == null ? "var(--muted)" : e.r20 >= 0 ? "var(--good)" : "var(--bad)"} stroke="var(--card)" strokeWidth="2"
          style={{ cursor: "pointer" }} onMouseEnter={() => onHover(e)} onClick={() => onHover(e)} />
      ))}
    </svg>
  );
}

export default function Timeline({ assetId, onChange }) {
  const [names, setNames] = useState({});
  const [q, setQ] = useState("");
  const [prices, setPrices] = useState([]);
  const [events, setEvents] = useState([]);
  const [hover, setHover] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => { assetNames().then(setNames).catch(setErr); }, []);
  useEffect(() => {
    if (!assetId) return;
    (async () => {
      try {
        const from = new Date(Date.now() - 400 * 864e5).toISOString().slice(0, 10);
        const [p, e] = await Promise.all([
          api("marketData", `/v1/assets/${assetId}/prices`, { params: { from, limit: 5000 } }),
          api("stats", `/v1/assets/${assetId}/events`),
        ]);
        setPrices(p.items); setEvents(e.items); setHover(null); setErr(null);
      } catch (e) { setErr(e); }
    })();
  }, [assetId]);

  const candidates = q ? Object.values(names).filter((a) => a.asset_type !== "index" &&
    (a.name.toLowerCase().includes(q.toLowerCase()) || (a.aliases || []).some((x) => x.toLowerCase().includes(q.toLowerCase())))).slice(0, 8) : [];
  const a = names[assetId];

  return (
    <div className="grid">
      <div className="card wide">
        <div className="row">
          <input placeholder="종목 검색 (삼성전자, 엔비디아, 비트코인…)" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 300 }} />
          {candidates.map((c) => <button key={c.asset_id} className="ghost" onClick={() => { onChange(c.asset_id); setQ(""); }}>{c.name}</button>)}
        </div>
        {!assetId && <p className="muted">이번 주 언급이나 종목별 표에서 종목을 누르거나, 위에서 검색하세요.</p>}
        {err && <div className="problem">{err.message}</div>}
      </div>
      {assetId && (<>
        <div className="card wide">
          <h2 style={{ marginBottom: 4 }}>{a?.name || assetId} <span className="muted" style={{ fontSize: 14 }}>{assetId} · 언급 {events.length}건</span></h2>
          <p className="muted">점 = 언급 시점(T0 종가). 초록은 20거래일 뒤 상승, 빨강은 하락, 회색은 아직 20일이 안 지남.</p>
          <Chart prices={prices} events={events} onHover={setHover} />
        </div>
        <div className="card wide">
          <table>
            <thead><tr><th>언급일</th><th>T0</th><th className="num">T0 종가</th><th className="num">5일</th><th className="num">20일</th><th className="num">60일</th><th className="num">20일 초과</th></tr></thead>
            <tbody>{[...events].reverse().map((e) => (
              <tr key={e.mention_id} className={hover?.mention_id === e.mention_id ? "hl" : ""}>
                <td>{dateOnly(e.published_at)}</td><td>{e.t0_date || "—"}</td><td className="num">{e.t0_close?.toLocaleString() ?? "—"}</td>
                <td className={"num " + (e.r5 > 0 ? "good" : e.r5 < 0 ? "bad" : "")}>{pct(e.r5)}</td>
                <td className={"num " + (e.r20 > 0 ? "good" : e.r20 < 0 ? "bad" : "")}>{pct(e.r20)}</td>
                <td className={"num " + (e.r60 > 0 ? "good" : e.r60 < 0 ? "bad" : "")}>{pct(e.r60)}</td>
                <td className="num">{pct(e.x20)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </>)}
    </div>
  );
}

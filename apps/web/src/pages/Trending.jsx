import { useEffect, useState } from "react";
import { api, assetNames, dateOnly, num, pct } from "../api";

// 이번 주 언급 급증 종목 + 그 종목의 "과거 언급 뒤 20일 평균" (stats 요약)
export default function Trending({ onPick }) {
  const [days, setDays] = useState(7);
  const [rows, setRows] = useState(null);
  const [names, setNames] = useState({});
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [t, n, s] = await Promise.all([
          api("mentions", "/v1/mentions/trending", { params: { days, limit: 30 } }),
          assetNames(),
          api("stats", "/v1/summaries", { params: { prefix: "asset:" } }),
        ]);
        const sum = Object.fromEntries(s.items.filter((i) => i.key.endsWith(":20")).map((i) => [i.key.slice(6, -3), i.value]));
        setRows(t.items.map((r) => ({ ...r, summary: sum[r.asset_id] })));
        setNames(n); setErr(null);
      } catch (e) { setErr(e); }
    })();
  }, [days]);

  return (
    <div className="grid">
      <div className="card wide">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 style={{ margin: 0 }}>최근 {days}일 언급 급증</h2>
          <span className="row" style={{ margin: 0 }}>
            {[7, 14, 30].map((d) => <button key={d} className={d === days ? "primary" : "ghost"} onClick={() => setDays(d)}>{d}일</button>)}
          </span>
        </div>
        <p className="muted">직전 {days}일 대비 언급이 늘어난 순. "과거 반응"은 그 종목의 이전 언급들 뒤 20거래일 평균 수익률입니다.</p>
        {err && <div className="problem">{err.message}</div>}
        {rows && rows.length === 0 && <p className="muted">이 기간에 언급이 없습니다. 데이터 탭에서 수집 현황을 확인하세요.</p>}
        {rows && rows.length > 0 && (
          <table>
            <thead><tr><th>종목</th><th className="num">언급</th><th className="num">직전</th><th className="num">채널</th><th className="num">조회수</th><th>마지막</th><th className="num">과거 반응(20일)</th></tr></thead>
            <tbody>
              {rows.map((r) => {
                const a = names[r.asset_id];
                const s = r.summary;
                return (
                  <tr key={r.asset_id} className="clickable" onClick={() => onPick(r.asset_id)}>
                    <td><b>{a?.name || r.asset_id}</b><div className="muted">{r.asset_id}</div></td>
                    <td className="num">{r.mentions}</td>
                    <td className="num muted">{r.prev_mentions}</td>
                    <td className="num">{r.channels}</td>
                    <td className="num">{num(r.views)}</td>
                    <td>{dateOnly(r.last_mentioned_at)}</td>
                    <td className={"num " + (s?.mean > 0 ? "good" : s?.mean < 0 ? "bad" : "")}>
                      {s && s.n ? <>{pct(s.mean)} <span className="muted">n={s.n}{s.low_sample ? "·참고" : ""}</span></> : <span className="muted">첫 언급</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

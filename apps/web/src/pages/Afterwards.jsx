import { useEffect, useState } from "react";
import { api, assetNames, pct } from "../api";

// 분석 페이지(수업 필수) — 언급 뒤 수익률 분포. 전체 · 시장별 · 채널(익명) · 종목별
function Histogram({ hist }) {
  if (!hist) return null;
  const max = Math.max(1, ...hist.map((b) => b.n));
  const label = (b) => (b.from <= -1 ? "<-20%" : b.to >= 9 ? ">+20%" : `${b.from * 100}~${b.to * 100}%`);
  return (
    <div className="hist">
      {hist.map((b, i) => (
        <div key={i} className="hist-col" title={`${label(b)}: ${b.n}건`}>
          <div className="hist-bar" style={{ height: `${(b.n / max) * 100}%`, background: b.from < 0 ? "var(--bad)" : "var(--good)" }} />
          <div className="hist-label">{label(b)}</div>
        </div>
      ))}
    </div>
  );
}

function Stat({ label, value, sub, cls }) {
  return <div className="card"><h3>{label}</h3><div className={"big " + (cls || "")}>{value}</div>{sub && <p className="muted">{sub}</p>}</div>;
}

export default function Afterwards({ onPick }) {
  const [horizon, setHorizon] = useState(20);
  const [scope, setScope] = useState("overall");
  const [sum, setSum] = useState(null);
  const [channels, setChannels] = useState([]);
  const [assets, setAssets] = useState([]);
  const [names, setNames] = useState({});
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, ch, as, n] = await Promise.all([
          api("stats", "/v1/summary", { params: { scope, horizon } }),
          api("stats", "/v1/summaries", { params: { prefix: "channel:" } }),
          api("stats", "/v1/summaries", { params: { prefix: "asset:" } }),
          assetNames(),
        ]);
        setSum(s.value);
        setChannels(ch.items.filter((i) => i.key.endsWith(`:${horizon}`)).map((i) => ({ id: i.key.slice(8, -(String(horizon).length + 1)), ...i.value })));
        setAssets(as.items.filter((i) => i.key.endsWith(`:${horizon}`)).map((i) => ({ id: i.key.slice(6, -(String(horizon).length + 1)), ...i.value }))
          .filter((a) => a.n > 0).sort((a, b) => b.n - a.n).slice(0, 20));
        setNames(n); setErr(null);
      } catch (e) { setErr(e); setSum(null); }
    })();
  }, [horizon, scope]);

  return (
    <div className="grid">
      <div className="card wide">
        <h2>언급 뒤 {horizon} 거래일, 주가는 어땠나</h2>
        <div className="row">
          <label>기간</label>
          {[5, 20, 60].map((h) => <button key={h} className={h === horizon ? "primary" : "ghost"} onClick={() => setHorizon(h)}>{h}일</button>)}
          <label style={{ marginLeft: 12 }}>범위</label>
          {[["overall", "전체"], ["market:KRX", "국내"], ["market:US", "미국"], ["market:CRYPTO", "코인"]].map(([k, l]) => (
            <button key={k} className={k === scope ? "primary" : "ghost"} onClick={() => setScope(k)}>{l}</button>
          ))}
        </div>
        <p className="muted">T0 = 게시일(또는 다음 거래일) 종가 기준. 초과수익 = 종목 수익률 − 같은 기간 벤치마크(코스피 · S&P500 · 비트코인) 수익률.</p>
        {err && <div className="problem">{err.message}</div>}
      </div>
      {sum && sum.n > 0 && (<>
        <Stat label="표본" value={`${sum.n}건`} sub={sum.low_sample ? "30건 미만 — 참고용" : "언급 건수"} />
        <Stat label="평균 수익률" value={pct(sum.mean)} sub={`중앙값 ${pct(sum.median)}`} cls={sum.mean >= 0 ? "good" : "bad"} />
        <Stat label="벤치마크 대비" value={pct(sum.excess_mean)} sub="초과수익 평균" cls={sum.excess_mean >= 0 ? "good" : "bad"} />
        <Stat label="상승 확률" value={`${Math.round(sum.win_rate * 100)}%`} sub={`하위 10% ${pct(sum.p10)} · 상위 10% ${pct(sum.p90)}`} />
        <div className="card wide"><h3>수익률 분포</h3><Histogram hist={sum.histogram} /></div>
      </>)}
      {sum && sum.n === 0 && <div className="card wide muted">아직 계산된 언급이 없습니다. 언급 뒤 {horizon}거래일이 지나야 값이 채워집니다.</div>}

      <div className="card">
        <h3>채널별 (익명)</h3>
        <table>
          <thead><tr><th>채널</th><th className="num">n</th><th className="num">평균</th><th className="num">초과</th></tr></thead>
          <tbody>{channels.map((c) => (
            <tr key={c.id}><td>채널 {c.id.replace("UC_SAMPLE_", "")}</td><td className="num">{c.n}</td>
              <td className={"num " + (c.mean > 0 ? "good" : "bad")}>{pct(c.mean)}</td><td className="num">{pct(c.excess_mean)}</td></tr>
          ))}</tbody>
        </table>
        <p className="muted">채널 실명은 공개하지 않습니다.</p>
      </div>
      <div className="card">
        <h3>종목별 (언급 많은 순)</h3>
        <table>
          <thead><tr><th>종목</th><th className="num">n</th><th className="num">평균</th><th className="num">상승</th></tr></thead>
          <tbody>{assets.map((a) => (
            <tr key={a.id} className="clickable" onClick={() => onPick(a.id)}>
              <td>{names[a.id]?.name || a.id}</td><td className="num">{a.n}</td>
              <td className={"num " + (a.mean > 0 ? "good" : "bad")}>{pct(a.mean)}</td><td className="num">{Math.round(a.win_rate * 100)}%</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { api, assetNames, pct } from "../api";

// 분석 페이지(수업 필수) — 언급 뒤 수익률 분포. 전체 · 시장별 · 테마 · 채널(익명) · 종목별. 거래량 반응까지.
function Histogram({ hist }) {
  if (!hist) return null;
  const max = Math.max(1, ...hist.map((b) => b.n));
  const label = (b) => (b.from <= -1 ? "<-20%" : b.to >= 9 ? ">+20%" : `${Math.round(b.from * 100)}~${Math.round(b.to * 100)}%`);
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

const SCOPES = [["overall", "종목·코인 전체"], ["market:KRX", "국내"], ["market:US", "미국"], ["market:CRYPTO", "코인"], ["kind:theme", "업종·테마"]];

export default function Afterwards({ onPick }) {
  const [horizon, setHorizon] = useState(20);
  const [scope, setScope] = useState("overall");
  const [sum, setSum] = useState(null);
  const [channels, setChannels] = useState([]);
  const [assets, setAssets] = useState([]);
  const [names, setNames] = useState({});
  const [anon, setAnon] = useState({});
  const [err, setErr] = useState(null);

  useEffect(() => { api("youtube", "/v1/channels").then((r) => setAnon(Object.fromEntries(r.items.map((c) => [c.channel_id, c])))).catch(() => {}); }, []);
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
        const suf = `:${horizon}`;
        setChannels(ch.items.filter((i) => i.key.endsWith(suf)).map((i) => ({ id: i.key.slice(8, -suf.length), ...i.value })).filter((c) => c.n >= 5).sort((a, b) => b.n - a.n));
        setAssets(as.items.filter((i) => i.key.endsWith(suf)).map((i) => ({ id: i.key.slice(6, -suf.length), ...i.value }))
          .filter((a) => a.n > 0 && (scope === "kind:theme" ? n[a.id]?.asset_type === "theme" : n[a.id]?.asset_type !== "theme"))
          .sort((a, b) => b.n - a.n).slice(0, 25));
        setNames(n); setErr(null);
      } catch (e) { setErr(e); setSum(null); }
    })();
  }, [horizon, scope]);

  const vol = sum?.vol_n ? `${sum.vol_ratio_median}배 (중앙값) · 늘어난 비율 ${Math.round(sum.vol_up_rate * 100)}%` : null;

  return (
    <div className="grid">
      <div className="card wide">
        <h2>언급 뒤 {horizon} 거래일, 주가는 어땠나</h2>
        <div className="row">
          <label>기간</label>
          {[5, 20, 60].map((h) => <button key={h} className={h === horizon ? "primary" : "ghost"} onClick={() => setHorizon(h)}>{h}일</button>)}
          <label style={{ marginLeft: 12 }}>범위</label>
          {SCOPES.map(([k, l]) => <button key={k} className={k === scope ? "primary" : "ghost"} onClick={() => setScope(k)}>{l}</button>)}
        </div>
        <p className="muted">T0 = 영상을 보고 처음 거래할 수 있는 날의 종가(국내 15:30, 미국 동부 16:00, 코인은 다음 일봉). 초과수익 = 종목 수익률 − 같은 기간 벤치마크(코스피 · S&P500 · 비트코인).
          업종·테마는 "반도체 급등"처럼 종목 없이 업종만 말한 제목을 대표 ETF로 잰 것이라 종목 통계와 섞지 않는다.</p>
        {err && <div className="problem">{err.message}</div>}
      </div>
      {sum && sum.n > 0 && (<>
        <Stat label="표본" value={`${sum.n.toLocaleString()}건`} sub={sum.low_sample ? "30건 미만 — 참고용" : "언급 건수 (기간이 지난 것만)"} />
        <Stat label="평균 수익률" value={pct(sum.mean)} sub={`중앙값 ${pct(sum.median)} · 하위 10% ${pct(sum.p10)} · 상위 10% ${pct(sum.p90)}`} cls={sum.mean >= 0 ? "good" : "bad"} />
        <Stat label="벤치마크 대비" value={pct(sum.excess_mean)} sub={`초과수익 평균 · 시장을 이긴 비율 ${sum.excess_win_rate != null ? Math.round(sum.excess_win_rate * 100) + "%" : "—"}`} cls={sum.excess_mean >= 0 ? "good" : "bad"} />
        <Stat label="상승 확률" value={`${Math.round(sum.win_rate * 100)}%`} sub="언급 뒤 수익률이 0보다 큰 비율" />
        <Stat label="거래량 반응" value={sum.vol_n ? `${sum.vol_ratio_median}배` : "—"} sub={vol ? `언급 뒤 5일 평균 ÷ 언급 전 20일 평균 · n=${sum.vol_n}` : "거래량 데이터 없음"} cls={sum.vol_ratio_median > 1 ? "warn" : ""} />
        {sum.disclosure_n > 0 && <Stat label="공시 동반 비율" value={`${Math.round(sum.disclosure_rate * 100)}%`} sub={`사건일 ±3일에 DART 공시가 있던 언급 (국내 종목 n=${sum.disclosure_n})`} />}
        <div className="card wide"><h3>수익률 분포</h3><Histogram hist={sum.histogram} /></div>
      </>)}
      {sum && sum.n === 0 && <div className="card wide muted">아직 계산된 언급이 없습니다. 언급 뒤 {horizon}거래일이 지나야 값이 채워집니다.</div>}

      <div className="card">
        <h3>채널별 (익명 · 표본 5건 이상)</h3>
        <div style={{ maxHeight: 420, overflow: "auto" }}>
          <table>
            <thead><tr><th>채널</th><th className="num">n</th><th className="num">평균</th><th className="num">초과</th><th className="num">상승</th></tr></thead>
            <tbody>{channels.map((c) => (
              <tr key={c.id}><td>채널 {anon[c.id]?.anon_code || "?"} <span className="muted">{anon[c.id]?.category}</span></td><td className="num">{c.n}</td>
                <td className={"num " + (c.mean > 0 ? "good" : "bad")}>{pct(c.mean)}</td><td className="num">{pct(c.excess_mean)}</td><td className="num">{Math.round(c.win_rate * 100)}%</td></tr>
            ))}</tbody>
          </table>
        </div>
        <p className="muted">채널 실명은 공개하지 않습니다. "누가 잘 맞혔나"가 아니라 유튜브 언급이라는 현상의 성적입니다.</p>
      </div>
      <div className="card">
        <h3>{scope === "kind:theme" ? "테마별" : "종목별"} (언급 많은 순)</h3>
        <div style={{ maxHeight: 420, overflow: "auto" }}>
          <table>
            <thead><tr><th>{scope === "kind:theme" ? "테마" : "종목"}</th><th className="num">n</th><th className="num">평균</th><th className="num">상승</th><th className="num">거래량</th></tr></thead>
            <tbody>{assets.map((a) => (
              <tr key={a.id} className="clickable" onClick={() => onPick(a.id)}>
                <td>{names[a.id]?.name || a.id}</td><td className="num">{a.n}</td>
                <td className={"num " + (a.mean > 0 ? "good" : "bad")}>{pct(a.mean)}</td><td className="num">{Math.round(a.win_rate * 100)}%</td>
                <td className="num">{a.vol_ratio_median ? `${a.vol_ratio_median}배` : "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

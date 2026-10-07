import { useState } from "react";
import { api, assetNames, assetSummaries, compact, dateOnly, num, pct, pct0, sign, MARKET_LABEL } from "../api";
import { Disclaimer, ErrorBox, Seg, SkeletonRows, Term, useLoad } from "../components";

export default function Home({ go }) {
  const [days, setDays] = useState(7);
  const [market, setMarket] = useState("ALL");
  const head = useLoad(() => Promise.all([api("youtube", "/v1/coverage", { ttl: 60e3 }), api("mentions", "/v1/coverage", { ttl: 60e3 }), api("stats", "/v1/coverage", { ttl: 60e3 })]), []);
  const trend = useLoad(async () => {
    const [t, names, sum] = await Promise.all([api("mentions", "/v1/mentions/trending", { params: { days, limit: 60, stance: "bull" }, ttl: 60e3 }), assetNames(), assetSummaries(20, "bull")]);
    return t.items.map((r) => ({ ...r, asset: names[r.asset_id], summary: sum[r.asset_id] }));
  }, [days]);
  const [yt, me, st] = head.data || [];
  const rows = (trend.data || []).filter((r) => market === "ALL" ? true : market === "THEME" ? r.asset?.asset_type === "theme" : (r.asset?.market === market && r.asset?.asset_type !== "theme")).slice(0, 25);

  return (
    <div className="page container">
      <section className="hero">
        <div>
          <div className="eyebrow" style={{ color: "#9db4ff" }}>HINDSIGHT · 유튜브 언급의 사후 성적표</div>
          <h1>유튜버가 오른다고 한 종목,<br />정말 올랐을까?</h1>
          <p>주식·코인 채널 {yt ? yt.channels : 51}개의 1년치 영상 제목에서 "오른다"고 한 종목을 찾아, 그 뒤 5·20·60거래일 주가를 셌다. 개별 영상이 아니라 1년치 전체의 평균이다.</p>
          <div className="flow"><span>YouTube 제목</span><i>→</i><span>종목·테마 매칭</span><i>→</i><span>시세·거래량·공시</span><i>→</i><span>언급 뒤 수익률</span></div>
        </div>
        <div className="kpis">
          <div className="kpi"><b>{yt ? num(yt.videos) : "—"}</b><span>영상 제목</span></div>
          <div className="kpi"><b>{me?.by_stance ? num(me.by_stance.bull) : "—"}</b><span>낙관 언급 <span style={{ opacity: .6 }}>/ 전체 {me ? num(me.mentions) : "—"}</span></span></div>
          <div className="kpi"><b>{st ? num(st.events) : "—"}</b><span>수익률 계산</span></div>
          <div className="kpi"><b>{me ? pct0(me.match_rate) : "—"}</b><span>제목 매칭 성공률</span></div>
        </div>
      </section>

      <div className="card">
        <div className="card-head">
          <div><h2>지금 유튜브가 오른다고 하는 종목</h2><p>최근 {days}일 <Term k="stance">낙관</Term> <Term k="mention">언급</Term>이 직전 {days}일보다 늘어난 순. 종목을 누르면 주가 위 언급 시점을 본다.</p></div>
          <div className="controls">
            <Seg value={days} onChange={setDays} options={[[7, "7일"], [14, "14일"], [30, "30일"]]} />
            <Seg value={market} onChange={setMarket} options={[["ALL", "전체"], ["KRX", "국내"], ["US", "미국"], ["CRYPTO", "코인"], ["THEME", "업종·테마"]]} />
          </div>
        </div>
        <ErrorBox error={trend.error} />
        {trend.loading && !trend.data ? <SkeletonRows n={8} /> : rows.length === 0 ? <p className="muted">해당 언급 없음.</p> : (
          <div className="table-wrap fade-in" style={{ opacity: trend.loading ? .6 : 1, transition: "opacity .2s" }}>
            <table>
              <thead><tr>
                <th>종목</th><th className="num"><Term k="mention">언급</Term></th><th className="num"><Term k="prev">직전</Term></th><th className="num"><Term k="surge">급증</Term></th>
                <th className="num"><Term k="channels">채널 수</Term></th><th className="num"><Term k="views">조회수</Term></th><th>마지막 언급</th><th className="num"><Term k="past">과거 낙관 언급 뒤 20일 평균</Term></th>
              </tr></thead>
              <tbody>
                {rows.map((r) => {
                  const a = r.asset; const s = r.summary; const surge = r.prev_mentions ? r.mentions / r.prev_mentions : null;
                  return (
                    <tr key={r.asset_id} className="clickable" onClick={() => go("ticker", r.asset_id)}>
                      <td className="name"><b>{a?.name || r.asset_id}</b><small>{a?.asset_type === "theme" ? "업종·테마 ETF" : MARKET_LABEL[a?.market] || a?.market} · {r.asset_id.split(":")[1]}</small></td>
                      <td className="num"><b>{r.mentions}</b></td>
                      <td className="num muted">{r.prev_mentions}</td>
                      <td className="num">{surge == null ? <span className="chip accent">신규</span> : <span className={"chip " + (surge >= 2 ? "up" : "")}>{surge.toFixed(1)}×</span>}</td>
                      <td className="num">{r.channels}</td>
                      <td className="num">{compact(r.views)}</td>
                      <td className="muted">{dateOnly(r.last_mentioned_at)}</td>
                      <td className={"num " + sign(s?.mean)}>{s && s.n ? <>{pct(s.mean)} <span className="muted" style={{ fontSize: 12 }}>n={s.n}</span></> : <span className="muted">첫 언급</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <Disclaimer />
      </div>
    </div>
  );
}

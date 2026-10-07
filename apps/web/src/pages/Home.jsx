import { useState } from "react";
import { api, assetNames, compact, dateOnly, num, pct, pct0, sign, MARKET_LABEL } from "../api";
import { Disclaimer, ErrorBox, Seg, SkeletonRows, Term, useLoad } from "../components";

// 홈 — 서비스가 무엇인지 한눈에 + 지금 유튜브에서 뜨는 종목
export default function Home({ go }) {
  const [days, setDays] = useState(7);
  const [market, setMarket] = useState("ALL");
  const head = useLoad(() => Promise.all([
    api("youtube", "/v1/coverage", { ttl: 60e3 }), api("mentions", "/v1/coverage", { ttl: 60e3 }), api("stats", "/v1/coverage", { ttl: 60e3 }),
  ]), []);
  const trend = useLoad(async () => {
    const [t, names, s] = await Promise.all([
      api("mentions", "/v1/mentions/trending", { params: { days, limit: 60 } }),
      assetNames(),
      api("stats", "/v1/summaries", { params: { prefix: "asset:" }, ttl: 5 * 60e3 }),
    ]);
    const sum = Object.fromEntries(s.items.filter((i) => i.key.endsWith(":20")).map((i) => [i.key.slice(6, -3), i.value]));
    return t.items.map((r) => ({ ...r, asset: names[r.asset_id], summary: sum[r.asset_id] }));
  }, [days]);

  const [yt, me, st] = head.data || [];
  const rows = (trend.data || []).filter((r) => market === "ALL" ? true : market === "THEME" ? r.asset?.asset_type === "theme" : (r.asset?.market === market && r.asset?.asset_type !== "theme")).slice(0, 25);

  return (
    <div className="page container">
      <section className="hero">
        <div className="eyebrow" style={{ color: "#9db4ff" }}>HINDSIGHT · 유튜브 언급의 사후 성적표</div>
        <h1>유튜버가 말한 종목,<br />그 뒤에 어떻게 됐나</h1>
        <p>주식·코인 유튜브 채널 <b style={{ color: "#fff" }}>{yt ? yt.channels : 51}개</b>의 1년치 영상 제목에서 종목을 찾아, 언급 뒤 <b style={{ color: "#fff" }}>5·20·60 거래일</b> 동안 주가가 실제로 어떻게 움직였는지 통계로 보여줍니다. 누가 맞혔나가 아니라, 유튜브 언급을 따라가면 평균적으로 어떻게 되는지를 봅니다.</p>
        <div className="kpis">
          <div className="kpi"><b>{yt ? num(yt.videos) : "—"}</b><span>영상 제목 수집</span></div>
          <div className="kpi"><b>{me ? num(me.mentions) : "—"}</b><span>종목·테마 언급</span></div>
          <div className="kpi"><b>{st ? num(st.events) : "—"}</b><span>언급 뒤 수익률 계산</span></div>
          <div className="kpi"><b>{me ? pct0(me.match_rate) : "—"}</b><span>제목 매칭 성공률</span></div>
        </div>
        <div className="steps">
          <div className="step"><b>① 수집</b>YouTube API로 매일 새 영상 제목</div>
          <div className="step"><b>② 매칭</b>제목 속 종목·별칭·업종을 사전으로</div>
          <div className="step"><b>③ 시세</b>국내·미국·코인 종가와 거래량, 공시</div>
          <div className="step"><b>④ 계산</b>언급 뒤 5·20·60일 수익률과 시장 대비</div>
        </div>
      </section>

      <div className="grid">
        <div className="card col-12">
          <div className="card-head">
            <div>
              <h2>지금 유튜브에서 뜨는 종목</h2>
              <p>최근 {days}일 동안 <Term k="mention">언급</Term>이 직전 {days}일보다 늘어난 순서입니다. 종목을 누르면 그 종목의 언급 시점과 주가를 함께 볼 수 있습니다.</p>
            </div>
            <div className="controls">
              <Seg value={days} onChange={setDays} options={[[7, "7일"], [14, "14일"], [30, "30일"]]} />
              <Seg value={market} onChange={setMarket} options={[["ALL", "전체"], ["KRX", "국내"], ["US", "미국"], ["CRYPTO", "코인"], ["THEME", "업종·테마"]]} />
            </div>
          </div>
          <ErrorBox error={trend.error} />
          {trend.loading && !trend.data ? <SkeletonRows n={8} /> : rows.length === 0 ? <p className="muted">이 조건에 해당하는 언급이 없습니다.</p> : (
            <div className="table-wrap fade-in" style={{ opacity: trend.loading ? .6 : 1, transition: "opacity .2s" }}>
              <table>
                <thead><tr>
                  <th>종목</th>
                  <th className="num"><Term k="mention">언급</Term></th>
                  <th className="num"><Term k="prev">직전</Term></th>
                  <th className="num"><Term k="surge">급증</Term></th>
                  <th className="num"><Term k="channels">채널 수</Term></th>
                  <th className="num"><Term k="views">조회수</Term></th>
                  <th>마지막 언급</th>
                  <th className="num"><Term k="past">과거 반응 (20일)</Term></th>
                </tr></thead>
                <tbody>
                  {rows.map((r) => {
                    const a = r.asset; const s = r.summary;
                    const surge = r.prev_mentions ? r.mentions / r.prev_mentions : null;
                    return (
                      <tr key={r.asset_id} className="clickable" onClick={() => go("ticker", r.asset_id)}>
                        <td className="name"><b>{a?.name || r.asset_id}</b><small>{a?.asset_type === "theme" ? "업종·테마 ETF" : MARKET_LABEL[a?.market] || a?.market} · {r.asset_id.split(":")[1]}</small></td>
                        <td className="num"><b>{r.mentions}</b></td>
                        <td className="num muted">{r.prev_mentions}</td>
                        <td className="num">{surge == null ? <span className="chip accent">신규</span> : <span className={"chip " + (surge >= 2 ? "up" : "")}>{surge.toFixed(1)}×</span>}</td>
                        <td className="num">{r.channels}</td>
                        <td className="num">{compact(r.views)}</td>
                        <td className="muted">{dateOnly(r.last_mentioned_at)}</td>
                        <td className={"num " + sign(s?.mean)}>{s && s.n ? <>{pct(s.mean)} <span className="muted" style={{ fontSize: 12 }}>n={s.n}{s.low_sample ? "·참고" : ""}</span></> : <span className="muted">첫 언급</span>}</td>
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
    </div>
  );
}

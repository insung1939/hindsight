import { useMemo, useState } from "react";
import { api, assetNames, channelMap, dateOnly, num, pct, pct0, sign, MARKET_LABEL, STANCES, STANCE_LABEL } from "../api";
import { Disclaimer, ErrorBox, SkeletonRows, Stat, Term, useLoad } from "../components";

function Chart({ prices, events, disclosures = [], news = [], onHover, hover }) {
  if (!prices?.length) return <p className="muted">시세가 없습니다.</p>;
  const W = 900, H = 260, P = 14, PB = 24;
  const t = (d) => new Date(d).getTime();
  const xs = prices.map((p) => t(p.trade_date)); const ys = prices.map((p) => p.close);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]; const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const X = (v) => P + ((v - x0) / (x1 - x0 || 1)) * (W - 2 * P);
  const Y = (v) => P + (1 - (v - y0) / (y1 - y0 || 1)) * (H - P - PB);
  const dense = events.length > 300;  // 삼성전자처럼 언급이 수천 건이면 점을 작고 옅게
  const path = prices.map((p, i) => `${i ? "L" : "M"}${X(t(p.trade_date))},${Y(p.close)}`).join(" ");
  const area = path + ` L${X(x1)},${H - PB} L${X(x0)},${H - PB} Z`;
  const months = []; let last = "";
  prices.forEach((p) => { const m = p.trade_date.slice(0, 7); if (m !== last) { months.push(p); last = m; } });
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="주가와 언급 시점">
      <defs><linearGradient id="g" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="var(--accent)" stopOpacity=".18" /><stop offset="1" stopColor="var(--accent)" stopOpacity="0" /></linearGradient></defs>
      {news.length > 0 && (() => { const nmax = Math.max(...news.map((n) => n.count), 1); return news.filter((n) => t(n.news_date) >= x0 && t(n.news_date) <= x1).map((n) => (
        <rect key={n.news_date} x={X(t(n.news_date)) - 2} width="4" y={H - PB - 2 - (n.count / nmax) * 40} height={(n.count / nmax) * 40} rx="1" fill="var(--accent)" opacity=".35"><title>{n.news_date} 기사 {n.count}건</title></rect>)); })()}
      <path d={area} fill="url(#g)" />
      <path d={path} fill="none" stroke="var(--text)" strokeOpacity=".7" strokeWidth="1.6" />
      {months.filter((_, i) => i % 2 === 0).map((p) => <text key={p.trade_date} x={X(t(p.trade_date))} y={H - 6} fontSize="10" fill="var(--muted)" textAnchor="middle" fontFamily="inherit">{p.trade_date.slice(2, 7)}</text>)}
      {disclosures.filter((d) => t(d.rcept_dt) >= x0 && t(d.rcept_dt) <= x1).map((d) => (
        <line key={d.rcept_no} x1={X(t(d.rcept_dt))} x2={X(t(d.rcept_dt))} y1={H - PB} y2={H - PB - 12} stroke="var(--warn)" strokeWidth="2"><title>{d.rcept_dt} 공시 · {d.kind} · {d.report_nm}</title></line>
      ))}
      {events.filter((e) => e.t0_date).map((e) => (
        <circle key={e.mention_id} cx={X(t(e.t0_date))} cy={Y(e.t0_close)} r={hover?.mention_id === e.mention_id ? 8 : dense ? 3.5 : 5.5} opacity={dense ? .55 : 1}
          fill={e.r20 == null ? "var(--muted)" : e.r20 >= 0 ? "var(--up)" : "var(--down)"} stroke="#fff" strokeWidth={dense ? 1 : 2} style={{ cursor: "pointer", transition: "r .15s" }}
          onMouseEnter={() => onHover(e)} onClick={() => onHover(e)} />
      ))}
    </svg>
  );
}

// 종목 — 한 종목의 언급 시점을 주가 위에
export default function Ticker({ assetId, go }) {
  const [q, setQ] = useState("");
  const [hover, setHover] = useState(null);
  const [limit, setLimit] = useState(200);
  const [stance, setStance] = useState("bull");
  const names = useLoad(() => assetNames(true), []);
  const chs = useLoad(channelMap, []);
  const data = useLoad(async () => {
    if (!assetId) return null;
    const from = new Date(Date.now() - 400 * 864e5).toISOString().slice(0, 10);
    const [p, e, d, s, n] = await Promise.all([
      api("marketData", `/v1/assets/${assetId}/prices`, { params: { from, limit: 5000 } }),
      api("stats", `/v1/assets/${assetId}/events`),
      api("marketData", "/v1/disclosures", { params: { asset_ids: assetId, from, limit: 5000 } }).then((r) => ({ items: r.items.filter((x) => ["실적", "계약", "자금조달", "주요사항"].includes(x.kind)) })).catch(() => ({ items: [] })),
      api("stats", "/v1/summary", { params: { scope: `asset:${assetId}`, horizon: 20, stance } }).then((r) => r.value).catch(() => null),
      api("marketData", "/v1/news-daily", { params: { asset_ids: assetId, from }, ttl: 5 * 60e3 }).catch(() => ({ items: [] })),
    ]);
    setHover(null);
    return { prices: p.items, events: e.items, disc: d.items, sum: s, news: n.items };
  }, [assetId, stance]);
  const all = names.data || {};
  const candidates = useMemo(() => {
    const s = q.trim().toLowerCase(); if (!s) return [];
    return Object.values(all).filter((a) => a.asset_type !== "index" && (a.name.toLowerCase().includes(s) || a.symbol.toLowerCase().includes(s) || (a.aliases || []).some((x) => x.toLowerCase().includes(s)))).slice(0, 8);
  }, [q, all]);
  const a = all[assetId]; const d = data.data; const sum = d?.sum;
  const shown = (d?.events || []).filter((e) => stance === "all" || e.stance === stance);
  const popular = ["KRX:005930", "KRX:000660", "US:NVDA", "US:TSLA", "CRYPTO:KRW-BTC", "KRX:091160"];

  return (
    <div className="page container">
      <div className="page-head">
        <div className="eyebrow">종목</div>
        <h1>{a ? a.name : "종목 하나를 골라 보세요"}</h1>
        <p>{a ? `${a.asset_type === "theme" ? "업종·테마 (대표 ETF)" : MARKET_LABEL[a.market]} · ${a.symbol} · 벤치마크 ${a.benchmark_id?.split(":")[1] || "—"}` : "주가 위에 언급 시점을 점으로. 빨강은 20거래일 뒤 올랐고 파랑은 내렸다."}</p>
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <input type="search" placeholder="종목 검색 — 삼성전자, 하닉, 엔비디아, 비트코인, 반도체… (Enter 로 첫 결과)" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && candidates[0]) { go("ticker", candidates[0].asset_id); setQ(""); } if (e.key === "Escape") setQ(""); }} autoFocus={!assetId} />
        <div className="controls" style={{ marginTop: 10 }}>
          {(q ? candidates : popular.map((id) => all[id]).filter(Boolean)).map((c) => (
            <button key={c.asset_id} className={"btn " + (c.asset_id === assetId ? "primary" : "")} onClick={() => { go("ticker", c.asset_id); setQ(""); }}>{c.name} <span className="muted" style={{ fontSize: 12 }}>{c.symbol}</span></button>
          ))}
          {q && candidates.length === 0 && <span className="muted">사전에 없는 이름</span>}
        </div>
      </div>
      <ErrorBox error={data.error} />
      {assetId && (
        <div className="grid">
          <div className="card col-12" style={{ padding: "12px 20px" }}><div className="controls"><Seg value={stance} onChange={setStance} options={STANCES} /><span className="muted" style={{ fontSize: 13 }}>{stance === "bull" ? "오른다고 한 언급만" : stance === "bear" ? "내린다고 한 언급만" : "논조 무관 전체"}</span></div></div>
          <div className="col-3"><Stat k="mention" label={`${STANCE_LABEL[stance] === "전체" ? "" : STANCE_LABEL[stance] + " "}언급`} loading={data.loading && !d} value={d ? `${num(shown.length)}건` : "—"} sub={d ? `전체 ${num(d.events.length)}건 · 최근 1년` : "최근 1년"} /></div>
          <div className="col-3"><Stat k="past" label="언급 뒤 20거래일 수익률 평균" loading={data.loading && !d} value={pct(sum?.mean)} cls={sign(sum?.mean)} sub={sum?.n ? `n=${sum.n}${sum.low_sample ? " · 참고용" : ""}` : "계산 전"} /></div>
          <div className="col-3"><Stat k="win" label="20거래일 뒤 오른 비율" loading={data.loading && !d} value={pct0(sum?.win_rate)} sub={sum ? `시장 대비 ${pct(sum.excess_mean)}` : ""} /></div>
          <div className="col-3"><Stat k="vol" label="거래량 비율" loading={data.loading && !d} value={sum?.vol_ratio_median ? `${sum.vol_ratio_median}배` : "—"} sub="언급 뒤 5일 ÷ 언급 전 20일" /></div>
          <div className="card col-12">
            <div className="card-head"><div><h3>주가와 언급 시점</h3><p>점 = <Term k="t0">사건일</Term> 종가 · 빨강 20일 뒤 상승 · 파랑 하락 · 회색 아직{d?.disc?.length > 0 && ` · 노란 눈금 = 주요 공시 ${d.disc.length}건`}{d?.news?.length > 0 && ` · 파란 막대 = 일별 뉴스 기사 수(네이버 증권 크롤링, ${d.news.length}일)`}</p></div>
              {hover && <span className="chip accent">{dateOnly(hover.published_at)} · {chs.data?.[hover.channel_id]?.title || "채널"} · 20일 {pct(hover.r20)}</span>}</div>
            {data.loading && !d ? <div className="sk" style={{ height: 260 }} /> : <Chart prices={d.prices} events={shown} disclosures={d.disc} news={d.news} onHover={setHover} hover={hover} />}
          </div>
          <div className="card col-12">
            <div className="card-head"><div><h3>언급별 기록</h3><p>최근 순 · 행에 올리면 차트의 점이 커진다</p></div></div>
            {data.loading && !d ? <SkeletonRows n={8} /> : (
              <div className="table-wrap" style={{ maxHeight: 520, overflowY: "auto" }}><table>
                <thead><tr><th>언급일</th><th>채널</th><th><Term k="stance">논조</Term></th><th><Term k="t0">T0</Term></th><th className="num">T0 종가</th><th className="num">5일</th><th className="num">20일</th><th className="num">60일</th><th className="num"><Term k="excess">20일 초과</Term></th><th className="num"><Term k="vol">거래량</Term></th><th><Term k="disc">공시</Term></th></tr></thead>
                <tbody>{[...shown].reverse().slice(0, limit).map((e) => (
                  <tr key={e.mention_id} className={hover?.mention_id === e.mention_id ? "hl" : ""} onMouseEnter={() => setHover(e)}>
                    <td>{dateOnly(e.published_at)}</td>
                    <td className="name"><b style={{ fontWeight: 600 }}>{chs.data?.[e.channel_id]?.title || e.channel_id.slice(0, 8)}</b></td>
                    <td><span className={"chip " + (e.stance === "bull" ? "up" : e.stance === "bear" ? "down" : "")}>{STANCE_LABEL[e.stance] || "중립"}</span></td>
                    <td className="muted">{e.t0_date || "—"}</td>
                    <td className="num">{e.t0_close?.toLocaleString() ?? "—"}</td>
                    <td className={"num " + sign(e.r5)}>{pct(e.r5)}</td>
                    <td className={"num " + sign(e.r20)}>{pct(e.r20)}</td>
                    <td className={"num " + sign(e.r60)}>{pct(e.r60)}</td>
                    <td className={"num " + sign(e.x20)}>{pct(e.x20)}</td>
                    <td className={"num " + (e.vol_ratio > 1.5 ? "warn" : "")}>{e.vol_ratio ? `${e.vol_ratio.toFixed(1)}배` : "—"}</td>
                    <td>{e.near_disclosure == null ? <span className="muted">—</span> : e.near_disclosure ? <span className="chip warn">있음</span> : <span className="muted">없음</span>}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
            {d && shown.length > limit && <div style={{ textAlign: "center", marginTop: 12 }}><button className="btn" onClick={() => setLimit(limit + 300)}>더 보기 ({num(shown.length - limit)}건 남음)</button></div>}
            <Disclaimer />
          </div>
        </div>
      )}
    </div>
  );
}

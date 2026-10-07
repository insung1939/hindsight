import { useState } from "react";
import { api, channelMap, compact, num, pct, pct0, sign, HORIZON_LABEL } from "../api";
import { Disclaimer, ErrorBox, Seg, SkeletonRows, Term, useLoad } from "../components";

const METRICS = [["excess_mean", "시장 대비 초과수익"], ["mean", "평균 수익률"], ["win_rate", "상승 확률"]];
const fmt = (m, v) => (m === "win_rate" ? pct0(v) : pct(v));

function RankCard({ r, ch, i, kind, metric }) {
  return (
    <div className={"rank " + kind}>
      <div className="pos-n">{i + 1}</div>
      <div className="who"><b>{ch?.title || r.channel_id}</b><small>{ch?.handle} · {ch?.category === "crypto" ? "코인" : "주식"} · 구독자 {compact(ch?.subscriber_count)} · 언급 {num(r.n)}건</small></div>
      <div className="val"><b className={sign(r[metric])}>{fmt(metric, r[metric])}</b><small>평균 {pct(r.mean)} · 상승 {pct0(r.win_rate)}</small></div>
    </div>
  );
}

function BarChart({ rows, metric, chs }) {
  if (!rows.length) return null;
  const vals = rows.map((r) => r[metric]);
  const max = Math.max(...vals.map(Math.abs), 0.01);
  const W = 720, rowH = 22, H = rows.length * rowH + 10, mid = W * 0.55;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="채널별 수익률 막대 차트">
      <line x1={mid} x2={mid} y1={0} y2={H} stroke="var(--border)" />
      {rows.map((r, i) => {
        const v = r[metric]; const w = (Math.abs(v) / max) * (W * 0.4); const y = i * rowH + 5;
        return (
          <g key={r.channel_id}>
            <text x={mid - 8} y={y + 13} textAnchor="end" fontSize="11" fill="var(--muted)" fontFamily="inherit">{(chs[r.channel_id]?.title || r.channel_id).slice(0, 16)}</text>
            <rect x={v >= 0 ? mid : mid - w} y={y} width={Math.max(w, 1.5)} height={rowH - 8} rx="4" fill={v >= 0 ? "var(--up)" : "var(--down)"} opacity=".85" />
            <text x={v >= 0 ? mid + w + 6 : mid - w - 6} y={y + 13} textAnchor={v >= 0 ? "start" : "end"} fontSize="11" fontWeight="700" fill="var(--text)" fontFamily="inherit">{fmt(metric, v)}</text>
          </g>
        );
      })}
    </svg>
  );
}

// 채널 — 언급 뒤 성적이 좋았던 채널과 나빴던 채널
export default function Channels() {
  const [horizon, setHorizon] = useState(20);
  const [metric, setMetric] = useState("excess_mean");
  const data = useLoad(() => Promise.all([api("stats", "/v1/channels/ranking", { params: { horizon, metric, min_n: 30, limit: 3 } }), channelMap()]), [horizon, metric]);
  const [rank, chs] = data.data || [null, {}];
  const all = rank?.all || [];

  return (
    <div className="page container">
      <div className="page-head">
        <div className="eyebrow">채널</div>
        <h1>어느 채널의 언급이 그 뒤에 잘 갔나</h1>
        <p>채널이 말한 종목들의 {HORIZON_LABEL[horizon].split(" ")[0]} 뒤 성적. 표본 30건 이상만. 시장과 종목이 다르니 실력보다 스타일 차이로 읽는다.</p>
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="controls">
          <label>기간</label><Seg value={horizon} onChange={setHorizon} options={[[5, "5거래일"], [20, "20거래일"], [60, "60거래일"]]} />
          <label style={{ marginLeft: 8 }}>기준</label><Seg value={metric} onChange={setMetric} options={METRICS} />
        </div>
        <details className="help"><summary>기준 설명</summary><div className="explain"><Term k="excess">시장 대비</Term>는 시장이 오른 효과를 뺀 값이라 채널 비교에 가장 공정하다. <Term k="n">표본</Term>이 적으면 몇 건에 평균이 휘둘린다.</div></details>
      </div>
      <ErrorBox error={data.error} />
      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card col-6">
          <div className="card-head"><div><h2>TOP 3</h2></div><span className="chip up">언급 뒤 성적 상위</span></div>
          {data.loading && !rank ? <SkeletonRows n={3} /> : <div className="rank-list">{(rank?.top || []).map((r, i) => <RankCard key={r.channel_id} r={r} ch={chs[r.channel_id]} i={i} kind="top" metric={metric} />)}</div>}
        </div>
        <div className="card col-6">
          <div className="card-head"><div><h2>BOTTOM 3</h2></div><span className="chip down">언급 뒤 성적 하위</span></div>
          {data.loading && !rank ? <SkeletonRows n={3} /> : <div className="rank-list">{(rank?.bottom || []).map((r, i) => <RankCard key={r.channel_id} r={r} ch={chs[r.channel_id]} i={i} kind="bottom" metric={metric} />)}</div>}
        </div>
        <div className="card col-12">
          <div className="card-head"><div><h3>채널 {all.length}개 · {METRICS.find((m) => m[0] === metric)[1]}</h3><p>빨강 좋음 · 파랑 나쁨</p></div></div>
          {data.loading && !rank ? <div className="sk" style={{ height: 300 }} /> : <BarChart rows={all} metric={metric} chs={chs} />}
        </div>
        <div className="card col-12">
          <div className="card-head"><div><h3>전체 표</h3></div></div>
          {data.loading && !rank ? <SkeletonRows n={8} /> : (
            <div className="table-wrap" style={{ maxHeight: 520, overflowY: "auto" }}><table>
              <thead><tr><th>#</th><th>채널</th><th>분류</th><th className="num">구독자</th><th className="num"><Term k="n">n</Term></th><th className="num">평균</th><th className="num">중앙값</th><th className="num"><Term k="win">상승</Term></th><th className="num"><Term k="excess">시장 대비</Term></th><th className="num"><Term k="xwin">시장 이김</Term></th><th className="num"><Term k="vol">거래량</Term></th></tr></thead>
              <tbody>{all.map((r, i) => { const c = chs[r.channel_id]; return (
                <tr key={r.channel_id}>
                  <td className="muted">{i + 1}</td>
                  <td className="name"><b>{c?.title || r.channel_id}</b><small>{c?.handle}</small></td>
                  <td><span className={"chip " + (c?.category === "crypto" ? "warn" : "accent")}>{c?.category === "crypto" ? "코인" : "주식"}</span></td>
                  <td className="num">{compact(c?.subscriber_count)}</td>
                  <td className="num">{num(r.n)}</td>
                  <td className={"num " + sign(r.mean)}>{pct(r.mean)}</td>
                  <td className={"num " + sign(r.median)}>{pct(r.median)}</td>
                  <td className="num">{pct0(r.win_rate)}</td>
                  <td className={"num " + sign(r.excess_mean)}>{pct(r.excess_mean)}</td>
                  <td className="num">{pct0(r.excess_win_rate)}</td>
                  <td className="num">{r.vol_ratio_median ? r.vol_ratio_median + "배" : "—"}</td>
                </tr>); })}</tbody>
            </table></div>
          )}
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}

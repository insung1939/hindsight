import { useState } from "react";
import { api, assetNames, num, pct, pct0, sign, HORIZON_LABEL } from "../api";
import { Disclaimer, ErrorBox, GLOSSARY, Histogram, Seg, SkeletonRows, Stat, Term, useLoad } from "../components";

const SCOPES = [["overall", "종목·코인 전체"], ["market:KRX", "국내"], ["market:US", "미국"], ["market:CRYPTO", "코인"], ["kind:theme", "업종·테마"]];

// 분석 — 언급을 따라가면 평균적으로 어떻게 되나
export default function Analysis({ go }) {
  const [horizon, setHorizon] = useState(20);
  const [scope, setScope] = useState("overall");
  const sum = useLoad(() => api("stats", "/v1/summary", { params: { scope, horizon } }).then((r) => r.value), [scope, horizon]);
  const markets = useLoad(() => Promise.all(SCOPES.map(([k]) => api("stats", "/v1/summary", { params: { scope: k, horizon } }).then((r) => [k, r.value]).catch(() => [k, null]))), [horizon]);
  const assets = useLoad(async () => {
    const [s, names] = await Promise.all([api("stats", "/v1/summaries", { params: { prefix: "asset:" }, ttl: 5 * 60e3 }), assetNames()]);
    const suf = `:${horizon}`;
    return s.items.filter((i) => i.key.endsWith(suf)).map((i) => ({ id: i.key.slice(6, -suf.length), asset: names[i.key.slice(6, -suf.length)], ...i.value })).filter((a) => a.n > 0);
  }, [horizon]);
  const v = sum.data; const isTheme = scope === "kind:theme";
  const list = (assets.data || []).filter((a) => isTheme ? a.asset?.asset_type === "theme" : scope.startsWith("market:") ? a.asset?.market === scope.split(":")[1] && a.asset?.asset_type !== "theme" : a.asset?.asset_type !== "theme").sort((a, b) => b.n - a.n).slice(0, 20);

  return (
    <div className="page container">
      <div className="page-head">
        <div className="eyebrow">분석</div>
        <h1>언급 뒤 {HORIZON_LABEL[horizon].split(" ")[0]}, 주가는 어땠나</h1>
        <p>유튜브에서 어떤 종목이 언급된 뒤 실제 주가가 어떻게 움직였는지를 1년치 언급 전체로 셉니다. 개별 영상의 적중이 아니라 "유튜브 언급"이라는 현상의 평균 성적입니다.</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="controls">
          <label>기간</label><Seg value={horizon} onChange={setHorizon} options={[[5, "5거래일 · 1주"], [20, "20거래일 · 1개월"], [60, "60거래일 · 3개월"]]} />
          <label style={{ marginLeft: 8 }}>범위</label><Seg value={scope} onChange={setScope} options={SCOPES} />
        </div>
        <div className="explain" style={{ marginTop: 12 }}>
          <b>읽는 법.</b> <Term k="horizon">{HORIZON_LABEL[horizon]} 수익률</Term>은 <Term k="t0">사건일</Term> 종가 대비 변화율입니다. <Term k="excess">초과수익</Term>이 0 근처면 종목이 오른 건 시장이 오른 덕이고, <Term k="win">상승 확률</Term>이 50% 근처면 언급은 방향 정보가 아닙니다. <Term k="vol">거래량 비율</Term>이 1보다 작으면 거래는 언급 <b>전</b>에 더 몰렸다는 뜻입니다.
          {isTheme && <> <Term k="theme">업종·테마</Term>는 종목 없이 "반도체 급등"처럼 업종만 말한 제목을 대표 ETF로 잰 것이라 종목 통계와 섞지 않습니다.</>}
        </div>
      </div>

      <ErrorBox error={sum.error} />
      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="col-3"><Stat k="n" label="표본" loading={sum.loading && !v} value={v ? `${num(v.n)}건` : "—"} sub={v?.low_sample ? "30건 미만 — 참고용" : "기간이 지나 계산된 언급"} /></div>
        <div className="col-3"><Stat k="horizon" label="평균 수익률" loading={sum.loading && !v} value={pct(v?.mean)} cls={sign(v?.mean)} sub={v ? `중앙값 ${pct(v.median)} · 하위 10% ${pct(v.p10)} · 상위 10% ${pct(v.p90)}` : ""} /></div>
        <div className="col-3"><Stat k="excess" label="시장 대비 (초과수익)" loading={sum.loading && !v} value={pct(v?.excess_mean)} cls={sign(v?.excess_mean)} sub={v ? `시장을 이긴 비율 ${pct0(v.excess_win_rate)}` : ""} /></div>
        <div className="col-3"><Stat k="win" label="상승 확률" loading={sum.loading && !v} value={pct0(v?.win_rate)} sub="수익률이 0보다 큰 비율" /></div>
        <div className="col-3"><Stat k="vol" label="거래량 비율" loading={sum.loading && !v} value={v?.vol_ratio_median ? `${v.vol_ratio_median}배` : "—"} cls={v?.vol_ratio_median > 1 ? "warn" : ""} sub={v?.vol_n ? `거래량이 늘어난 언급 ${pct0(v.vol_up_rate)} · n=${num(v.vol_n)}` : "거래량 데이터 없음"} /></div>
        {v?.disclosure_n > 0 && <div className="col-3"><Stat k="disc" label="주요 공시 동반" loading={false} value={pct0(v.disclosure_rate)} sub={`사건일 ±3일 안에 DART 주요 공시 · 국내 n=${num(v.disclosure_n)}`} /></div>}
        <div className={v?.disclosure_n > 0 ? "card col-6" : "card col-9"}>
          <div className="card-head"><div><h3>{HORIZON_LABEL[horizon].split(" ")[0]} 수익률 분포</h3><p>왼쪽(파랑)은 내린 언급, 오른쪽(빨강)은 오른 언급의 건수</p></div></div>
          <Histogram hist={v?.histogram} loading={sum.loading} />
        </div>
      </div>

      <div className="grid">
        <div className="card col-6">
          <div className="card-head"><div><h3>범위별 비교 ({HORIZON_LABEL[horizon].split(" ")[0]})</h3><p>같은 기간, 시장별로 언급의 성적이 어떻게 다른가</p></div></div>
          {markets.loading && !markets.data ? <SkeletonRows n={5} /> : (
            <div className="table-wrap"><table>
              <thead><tr><th>범위</th><th className="num">표본</th><th className="num">평균</th><th className="num">상승</th><th className="num">시장 대비</th><th className="num">거래량</th></tr></thead>
              <tbody>{(markets.data || []).map(([k, m]) => (
                <tr key={k} className={"clickable " + (k === scope ? "hl" : "")} onClick={() => setScope(k)}>
                  <td><b>{SCOPES.find((s) => s[0] === k)[1]}</b></td>
                  <td className="num">{m?.n ? num(m.n) : "—"}</td>
                  <td className={"num " + sign(m?.mean)}>{pct(m?.mean)}</td>
                  <td className="num">{pct0(m?.win_rate)}</td>
                  <td className={"num " + sign(m?.excess_mean)}>{pct(m?.excess_mean)}</td>
                  <td className="num">{m?.vol_ratio_median ? m.vol_ratio_median + "배" : "—"}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
        </div>
        <div className="card col-6">
          <div className="card-head"><div><h3>{isTheme ? "테마별" : "종목별"} · 언급 많은 순</h3><p>누르면 그 {isTheme ? "테마" : "종목"}의 언급 시점과 주가를 봅니다</p></div></div>
          {assets.loading && !assets.data ? <SkeletonRows n={8} /> : (
            <div className="table-wrap" style={{ maxHeight: 440, overflowY: "auto" }}><table>
              <thead><tr><th>{isTheme ? "테마" : "종목"}</th><th className="num">n</th><th className="num">평균</th><th className="num">상승</th><th className="num">거래량</th></tr></thead>
              <tbody>{list.map((a) => (
                <tr key={a.id} className="clickable" onClick={() => go("ticker", a.id)}>
                  <td className="name"><b>{a.asset?.name || a.id}</b><small>{a.id}</small></td>
                  <td className="num">{num(a.n)}</td>
                  <td className={"num " + sign(a.mean)}>{pct(a.mean)}</td>
                  <td className="num">{pct0(a.win_rate)}</td>
                  <td className="num">{a.vol_ratio_median ? a.vol_ratio_median + "배" : "—"}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
        </div>
        <div className="card col-12 flat">
          <div className="card-head"><div><h3>용어 설명</h3><p>표와 숫자에 쓰인 말들. 본문에서 점선 밑줄이 있는 말에 마우스를 올려도 같은 설명이 나옵니다.</p></div></div>
          <dl className="glossary">{["mention", "t0", "horizon", "excess", "win", "vol", "disc", "n", "theme"].map((k) => <div key={k}><dt>{GLOSSARY[k][0]}</dt><dd>{GLOSSARY[k][1]}</dd></div>)}</dl>
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}

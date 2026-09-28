import { useEffect, useState } from "react";
import { api, dateOnly, num } from "../api";

// 수업 필수 페이지 — 데이터 출처 · 채널(익명) · 수집 현황 · 매칭 성공률 · 못 잡은 제목
const SOURCES = [
  ["채널·영상 메타(제목·설명·게시일·조회수)", "YouTube Data API v3 · Google", "https://developers.google.com/youtube/v3", "Open API (키) · 검색 대신 채널 업로드 목록만 조회"],
  ["상장사 이름·종목코드", "DART OpenAPI corpCode · 금융감독원", "https://opendart.fss.or.kr", "Open API (키) · 월 1회"],
  ["국내 일별 시세", "금융위원회_주식시세정보 · 공공데이터포털", "https://www.data.go.kr/data/15094808/openapi.do", "Open API (키) · 없으면 Yahoo 국내 심볼로 대체"],
  ["미국 시세 · 코스피/S&P500 지수", "Yahoo Finance chart API", "https://finance.yahoo.com", "HTTP JSON (키 불필요)"],
  ["코인 마켓 목록 · 일봉", "업비트 Open API · 두나무", "https://docs.upbit.com", "Open API (키 불필요)"],
];

export default function DataPage() {
  const [yt, setYt] = useState(null);
  const [cov, setCov] = useState(null);
  const [channels, setChannels] = useState([]);
  const [unmatched, setUnmatched] = useState([]);
  const [assets, setAssets] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [y, c, ch, u, a] = await Promise.all([
          api("youtube", "/v1/coverage"), api("mentions", "/v1/coverage"), api("youtube", "/v1/channels"),
          api("mentions", "/v1/unmatched", { params: { limit: 20 } }), api("marketData", "/v1/assets", { params: { limit: 5000 } }),
        ]);
        setYt(y); setCov(c); setChannels(ch.items); setUnmatched(u.items);
        const by = {};
        a.items.forEach((x) => { by[x.market] = by[x.market] || { total: 0, tracked: 0 }; by[x.market].total++; if (x.tracked) by[x.market].tracked++; });
        setAssets(by); setErr(null);
      } catch (e) { setErr(e); }
    })();
  }, []);

  return (
    <div className="grid">
      <div className="card wide">
        <h2>데이터 출처</h2>
        <table>
          <thead><tr><th>데이터</th><th>명칭 · 기관</th><th>방식</th></tr></thead>
          <tbody>{SOURCES.map(([d, n, u, m]) => <tr key={d}><td>{d}</td><td><a href={u} target="_blank" rel="noreferrer">{n}</a></td><td>{m}</td></tr>)}</tbody>
        </table>
        <p className="muted">자막·댓글은 수집하지 않습니다. 채널은 익명 코드로만 표시합니다.</p>
      </div>
      {err && <div className="card wide problem">{err.message}</div>}
      <div className="card">
        <h3>영상 수집 (youtube)</h3>
        {yt && <>
          <div className="big">{num(yt.videos)}<span className="muted" style={{ fontSize: 14 }}> 편</span></div>
          <p className="muted">채널 {yt.channels}개 · {dateOnly(yt.first_published)} ~ {dateOnly(yt.last_published)}
            {Object.entries(yt.by_category).map(([k, v]) => ` · ${k} ${v}`)}</p>
        </>}
      </div>
      <div className="card">
        <h3>종목 매칭 (mentions)</h3>
        {cov && <>
          <div className="big">{Math.round(cov.match_rate * 100)}%</div>
          <div className="bar"><i style={{ width: `${cov.match_rate * 100}%` }} /></div>
          <p className="muted">영상 {cov.videos_seen}편 중 {cov.videos_matched}편에서 종목을 찾음 · 언급 {cov.mentions}건 · 종목 {cov.assets}개</p>
        </>}
      </div>
      <div className="card">
        <h3>종목 사전 (market-data)</h3>
        {assets && <table><thead><tr><th>시장</th><th className="num">사전</th><th className="num">시세 수집</th></tr></thead>
          <tbody>{Object.entries(assets).map(([m, v]) => <tr key={m}><td>{m}</td><td className="num">{v.total}</td><td className="num">{v.tracked}</td></tr>)}</tbody></table>}
        <p className="muted">사전에 있어도 언급되기 전엔 시세를 긁지 않습니다.</p>
      </div>
      <div className="card">
        <h3>채널 (익명)</h3>
        <table><thead><tr><th>코드</th><th>분류</th><th className="num">구독자</th></tr></thead>
          <tbody>{channels.map((c) => <tr key={c.channel_id}><td>채널 {c.anon_code}</td><td>{c.category}</td><td className="num">{num(c.subscriber_count)}</td></tr>)}</tbody></table>
      </div>
      <div className="card wide">
        <h3>종목을 못 잡은 제목 (최근 20개) — 별칭 사전 보강 재료</h3>
        {unmatched.length === 0 ? <p className="muted">없음</p> : <ul>{unmatched.map((u) => <li key={u.video_id}>{u.title} <span className="muted">{dateOnly(u.published_at)}</span></li>)}</ul>}
      </div>
    </div>
  );
}

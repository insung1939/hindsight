import { useEffect, useState } from "react";
import { api, dateOnly, num } from "../api";

// 수업 필수 페이지 — "어떤 소스에서, 어떻게 가공해, 얼마나 쌓였나" 를 숫자로. 출처 · 파이프라인 단계별 건수 · 채널(익명) · 매칭 성공률 · 못 잡은 제목
const SOURCES = [
  ["영상 제목·설명·게시일·조회수", "YouTube Data API v3 · Google", "https://developers.google.com/youtube/v3", "Open API (키) · 검색 대신 채널 업로드 목록(1유닛)만", "youtube"],
  ["상장사 이름·종목코드·DART 고유번호", "DART OpenAPI corpCode · 금융감독원", "https://opendart.fss.or.kr", "Open API (키) · 월 1회", "dart"],
  ["국내 일별 종가·거래량", "금융위원회_주식시세정보 · 공공데이터포털", "https://www.data.go.kr/data/15094808/openapi.do", "Open API (키) · 없으면 Yahoo 국내 심볼로 대체", "datagokr"],
  ["미국 시세 · 지수 · 업종 ETF 20개 · 거래량", "Yahoo Finance chart API", "https://finance.yahoo.com", "HTTP JSON (키 불필요)", "yahoo"],
  ["코인 마켓 목록 · 일봉 종가·거래량", "업비트 Open API · 두나무", "https://docs.upbit.com", "Open API (키 불필요)", "upbit"],
  ["공시 목록(실적·계약·자금조달·주요사항…)", "DART 공시검색 list.json · 금융감독원", "https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001", "Open API (키) · 언급된 국내 종목만", "disclosures"],
];

function Step({ n, title, big, unit, sub }) {
  return (
    <div className="card step">
      <div className="step-n">{n}</div>
      <h3>{title}</h3>
      <div className="big">{big ?? "—"}<span className="muted" style={{ fontSize: 14 }}> {unit}</span></div>
      {sub && <p className="muted">{sub}</p>}
    </div>
  );
}

export default function DataPage() {
  const [yt, setYt] = useState(null);
  const [cov, setCov] = useState(null);
  const [mk, setMk] = useState(null);
  const [st, setSt] = useState(null);
  const [channels, setChannels] = useState([]);
  const [unmatched, setUnmatched] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [y, c, ch, u, m, s] = await Promise.all([
          api("youtube", "/v1/coverage"), api("mentions", "/v1/coverage"), api("youtube", "/v1/channels"),
          api("mentions", "/v1/unmatched", { params: { limit: 20 } }), api("marketData", "/v1/coverage"), api("stats", "/v1/coverage"),
        ]);
        setYt(y); setCov(c); setChannels(ch.items); setUnmatched(u.items); setMk(m); setSt(s); setErr(null);
      } catch (e) { setErr(e); }
    })();
  }, []);

  const status = (k) => {
    if (!mk) return null;
    if (k === "disclosures") return mk.disclosures ? `${num(mk.disclosures)}건 · 종목 ${mk.disclosure_assets}개` : "키 대기";
    if (k === "yahoo" || k === "upbit" || k === "datagokr") return `시세 ${num(mk.prices)}행 (거래량 ${Math.round(mk.prices_with_volume / Math.max(1, mk.prices) * 100)}%) · ~${mk.last_trade_date}`;
    if (k === "dart") return `국내 종목 ${mk.assets_by_market?.KRX?.total ?? 0}개 (테마 ${mk.assets_by_market?.KRX?.theme ?? 0})`;
    if (k === "youtube" && yt) return `채널 ${yt.channels} · 영상 ${num(yt.videos)}`;
    return null;
  };
  const byCat = channels.reduce((a, c) => ({ ...a, [c.category]: (a[c.category] || 0) + 1 }), {});

  return (
    <div className="grid">
      <div className="card wide">
        <h2>데이터 파이프라인 — 매일 1회, 다섯 단계</h2>
        <p className="muted">외부 API에서 받아(①②) → 종목·테마로 바꾸고(③) → 시세·거래량을 붙여(④) → 언급 뒤 수익률을 계산한다(⑤). 화면은 계산된 결과만 읽는다.</p>
        {err && <div className="problem">{err.message}</div>}
      </div>
      <Step n="①" title="영상 수집 (youtube)" big={yt && num(yt.videos)} unit="편"
        sub={yt && `채널 ${yt.channels}개 · ${dateOnly(yt.first_published)} ~ ${dateOnly(yt.last_published)}`} />
      <Step n="②" title="종목·테마 사전 (market-data)" big={mk && num(Object.values(mk.assets_by_market).reduce((a, v) => a + v.total, 0))} unit="개"
        sub={mk && Object.entries(mk.assets_by_market).map(([k, v]) => `${k} ${v.total}`).join(" · ")} />
      <Step n="③" title="제목 → 종목 매칭 (mentions)" big={cov && `${Math.round(cov.match_rate * 100)}%`} unit="성공률"
        sub={cov && `영상 ${num(cov.videos_seen)}편 중 ${num(cov.videos_matched)}편 · 언급 ${num(cov.mentions)}건 · 종목·테마 ${cov.assets}개`} />
      <Step n="④" title="시세·거래량 (market-data)" big={mk && num(mk.prices)} unit="행"
        sub={mk && `추적 종목 ${Object.values(mk.assets_by_market).reduce((a, v) => a + v.tracked, 0)}개 · 거래량 포함 ${Math.round(mk.prices_with_volume / Math.max(1, mk.prices) * 100)}% · 마지막 ${mk.last_trade_date}`} />
      <Step n="⑤" title="언급 뒤 수익률 (stats)" big={st && num(st.events)} unit="건"
        sub={st && `5일 ${num(st.r5_filled)} · 20일 ${num(st.r20_filled)} · 60일 ${num(st.r60_filled)} 채워짐 · 거래량 비율 ${num(st.vol_ratio_filled)} · 테마 ${num(st.events_theme)}`} />

      <div className="card wide">
        <h2>데이터 출처</h2>
        <table>
          <thead><tr><th>데이터</th><th>명칭 · 기관</th><th>방식</th><th>현재</th></tr></thead>
          <tbody>{SOURCES.map(([d, n, u, m, k]) => <tr key={d}><td>{d}</td><td><a href={u} target="_blank" rel="noreferrer">{n}</a></td><td className="muted">{m}</td><td>{status(k) || "—"}</td></tr>)}</tbody>
        </table>
        <p className="muted">자막·댓글은 수집하지 않습니다. 채널은 익명 코드로만 표시합니다. 인증키는 서버 환경변수에만 둡니다.</p>
      </div>

      <div className="card">
        <h3>채널 선정 — 사람이 고르지 않았다</h3>
        <div className="big">{channels.length}<span className="muted" style={{ fontSize: 14 }}> 개</span></div>
        <p className="muted">주식 {byCat.stock || 0} · 코인 {byCat.crypto || 0}. YouTube 검색으로 후보 547개를 모아 구독자·업로드 빈도·제목의 종목 언급률·쇼츠 비율을 재고 두 단계 규칙으로 걸렀다.</p>
        <table>
          <thead><tr><th>단</th><th>구독자</th><th>언급률</th></tr></thead>
          <tbody>
            <tr><td>A 대형 영향력</td><td>100만 이상</td><td>15% 이상</td></tr>
            <tr><td>B 종목 집중</td><td>주식 5만 · 코인 10만 이상</td><td>30% 이상</td></tr>
          </tbody>
        </table>
        <p className="muted">공통: 45일 내 활동 · 쇼츠 50% 이하 · 방송사·증권사·거래소 제외. 구독자 373만 채널도 제목에 종목이 2%뿐이면 제외됐다.</p>
      </div>
      <div className="card">
        <h3>채널 (익명)</h3>
        <div style={{ maxHeight: 320, overflow: "auto" }}>
          <table><thead><tr><th>코드</th><th>분류</th><th className="num">구독자</th></tr></thead>
            <tbody>{channels.map((c) => <tr key={c.channel_id}><td>채널 {c.anon_code}</td><td>{c.category}</td><td className="num">{num(c.subscriber_count)}</td></tr>)}</tbody></table>
        </div>
      </div>
      <div className="card">
        <h3>매칭 규칙</h3>
        <ul className="muted" style={{ paddingLeft: 18, margin: 0, fontSize: 13, lineHeight: 1.6 }}>
          <li>사전(이름·별칭)을 긴 표현부터 정확 매칭. "삼성전자우"가 "삼성전자"보다 먼저</li>
          <li>흔한 단어(삼성·현대·KT·은행…)는 단독 매칭 금지. "한국은행" 같은 표현은 먼저 지움</li>
          <li>종목이 없어도 "반도체 급등"처럼 업종이 나오면 테마 사건으로 세고 대표 ETF로 잰다</li>
          <li>자동 수집 코인은 코인 문맥이 있을 때만. 못 잡은 제목은 버리지 않고 남긴다</li>
        </ul>
      </div>
      <div className="card wide">
        <h3>종목을 못 잡은 제목 (최근 20개) — 사전 보강 재료</h3>
        {unmatched.length === 0 ? <p className="muted">없음</p> : <ul>{unmatched.map((u) => <li key={u.video_id}>{u.title} <span className="muted">{dateOnly(u.published_at)}</span></li>)}</ul>}
      </div>
    </div>
  );
}

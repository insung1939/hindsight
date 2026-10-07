import { api, channelMap, compact, dateOnly, num, pct0, API_BASE } from "../api";
import { Disclaimer, ErrorBox, SkeletonRows, Term, useLoad } from "../components";

// 데이터 — 어떤 소스에서, 어떻게 가공해, 얼마나 쌓였나 (수업 필수 페이지)
const SOURCES = [
  { k: "youtube", name: "YouTube Data API v3", org: "Google", url: "https://developers.google.com/youtube/v3", what: "채널 51개의 영상 제목·설명·게시일·조회수", how: "검색(100유닛) 대신 채널 업로드 목록(1유닛)만 읽는다. 1년치 4만 4천 편을 약 1,500유닛에." },
  { k: "dart", name: "DART OpenAPI corpCode", org: "금융감독원", url: "https://opendart.fss.or.kr", what: "국내 전 상장사 이름·종목코드·고유번호", how: "종목 사전의 뼈대. 별칭(삼전·하닉…)과 업종 20개는 팀이 보강." },
  { k: "datagokr", name: "금융위원회 주식시세정보 V2", org: "공공데이터포털", url: "https://www.data.go.kr/data/15094808/openapi.do", what: "국내 일별 종가·거래량", how: "언급된 국내 종목만 매일. 키가 없거나 장애면 Yahoo 국내 심볼로 대체." },
  { k: "yahoo", name: "Yahoo Finance chart API", org: "Yahoo", url: "https://finance.yahoo.com", what: "미국 종가·거래량, 코스피·S&P500 지수, 업종 ETF 20개", how: "키 없이 HTTP JSON." },
  { k: "upbit", name: "업비트 Open API", org: "두나무", url: "https://docs.upbit.com", what: "KRW 마켓 목록·한글명, 일봉 종가·거래량", how: "마켓 목록으로 코인 사전을 자동으로 채운다. 언급된 코인만 시세 수집." },
  { k: "disclosures", name: "DART 공시검색", org: "금융감독원", url: "https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001", what: "접수일·공시명 → 실적·계약·자금조달·주요사항·지분·기타", how: "언급된 국내 종목의 1년치. 언급 전후 ±3일 주요 공시 유무를 판정." },
];

function Step({ n, title, big, unit, sub, loading }) {
  return <div className="st"><div className="k">{n}</div>{loading ? <div className="sk sk-big" /> : <div className="v">{big ?? "—"}<span className="muted" style={{ fontSize: 13, fontWeight: 600 }}> {unit}</span></div>}<div className="d">{sub}</div></div>;
}

export default function DataPage() {
  const d = useLoad(() => Promise.all([
    api("youtube", "/v1/coverage"), api("mentions", "/v1/coverage"), api("marketData", "/v1/coverage"), api("stats", "/v1/coverage"),
    channelMap(), api("mentions", "/v1/unmatched", { params: { limit: 20 } }),
  ]), []);
  const [yt, cov, mk, st, chs, un] = d.data || [];
  const chList = Object.values(chs || {}).sort((a, b) => (b.subscriber_count || 0) - (a.subscriber_count || 0));
  const loading = d.loading && !d.data;
  const status = (k) => {
    if (!mk) return "";
    if (k === "youtube" && yt) return `채널 ${yt.channels} · 영상 ${num(yt.videos)} · ~${dateOnly(yt.last_published)}`;
    if (k === "dart") return `국내 종목 ${num((mk.assets_by_market?.KRX?.total || 0) - (mk.assets_by_market?.KRX?.theme || 0))}개 · 테마 ${mk.assets_by_market?.KRX?.theme ?? 0}`;
    if (k === "datagokr") return `국내 추적 ${mk.assets_by_market?.KRX?.tracked ?? 0}개`;
    if (k === "yahoo") return `미국 ${mk.assets_by_market?.US?.total ?? 0} · 지수 ${mk.assets_by_market?.INDEX?.total ?? 0}`;
    if (k === "upbit") return `코인 사전 ${mk.assets_by_market?.CRYPTO?.total ?? 0} · 추적 ${mk.assets_by_market?.CRYPTO?.tracked ?? 0}`;
    if (k === "disclosures") return mk.disclosures ? `${num(mk.disclosures)}건 · 종목 ${mk.disclosure_assets} · ~${mk.last_disclosure_date}` : "키 대기";
    return "";
  };
  const totalAssets = mk ? Object.values(mk.assets_by_market).reduce((a, v) => a + v.total, 0) : null;
  const tracked = mk ? Object.values(mk.assets_by_market).reduce((a, v) => a + v.tracked, 0) : null;

  return (
    <div className="page container">
      <div className="page-head">
        <div className="eyebrow">데이터</div>
        <h1>어떤 데이터를, 어디서, 어떻게 가공했나</h1>
        <p>외부 공개 API 6개에서 받아 매일 한 번 다섯 단계로 가공합니다. 아래 숫자는 지금 데이터베이스에 쌓인 실제 건수입니다. API 문서는 <a href={API_BASE + "/docs"} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>Swagger</a>, 코드와 테이블 설명은 <a href="https://github.com/insung1939/hindsight" target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>GitHub</a>에 있습니다.</p>
      </div>
      <ErrorBox error={d.error} />

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-head"><div><h2>파이프라인 — 매일 07:10, GitHub Actions</h2><p>외부 API에서 받아(①②) → 종목·테마로 바꾸고(③) → 시세·거래량·공시를 붙여(④) → 언급 뒤 수익률을 계산한다(⑤). 화면은 계산된 결과만 읽습니다.</p></div></div>
        <div className="pipe">
          <Step n="① 영상 수집" loading={loading} big={yt && num(yt.videos)} unit="편" sub={yt && `채널 ${yt.channels}개 · ${dateOnly(yt.first_published)} ~ ${dateOnly(yt.last_published)}`} />
          <Step n="② 종목·테마 사전" loading={loading} big={totalAssets && num(totalAssets)} unit="개" sub={mk && Object.entries(mk.assets_by_market).map(([k, v]) => `${k} ${num(v.total)}`).join(" · ")} />
          <Step n="③ 제목 매칭" loading={loading} big={cov && pct0(cov.match_rate)} unit="성공률" sub={cov && `영상 ${num(cov.videos_seen)}편 중 ${num(cov.videos_matched)}편 · 언급 ${num(cov.mentions)}건 · ${cov.assets}개 종목·테마`} />
          <Step n="④ 시세·거래량·공시" loading={loading} big={mk && num(mk.prices)} unit="행" sub={mk && `추적 ${tracked}개 · 거래량 포함 ${pct0(mk.prices_with_volume / Math.max(1, mk.prices))} · 공시 ${num(mk.disclosures)}건`} />
          <Step n="⑤ 수익률 계산" loading={loading} big={st && num(st.events)} unit="건" sub={st && `20일 ${num(st.r20_filled)} · 60일 ${num(st.r60_filled)} 채워짐 · 테마 ${num(st.events_theme)}`} />
        </div>
      </div>

      <div className="grid">
        <div className="card col-12">
          <div className="card-head"><div><h2>데이터 출처 6개</h2><p>전부 공개 API. 인증키는 서버 환경변수에만 두고 저장소·화면에는 없습니다. 자막·댓글은 수집하지 않습니다.</p></div></div>
          <div className="table-wrap"><table>
            <thead><tr><th>명칭 · 기관</th><th>가져오는 것</th><th>어떻게 쓰나</th><th>지금</th></tr></thead>
            <tbody>{SOURCES.map((s) => (
              <tr key={s.k}>
                <td className="name"><b><a href={s.url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>{s.name}</a></b><small>{s.org}</small></td>
                <td>{s.what}</td>
                <td className="muted" style={{ fontSize: 13 }}>{s.how}</td>
                <td className="muted" style={{ fontSize: 13, whiteSpace: "nowrap" }}>{loading ? <span className="sk sk-line" style={{ display: "inline-block", width: 120 }} /> : status(s.k)}</td>
              </tr>
            ))}</tbody>
          </table></div>
        </div>

        <div className="card col-6">
          <div className="card-head"><div><h3>채널 {chList.length}개 — 사람이 고르지 않았다</h3><p>YouTube 검색으로 후보 547개를 모아 구독자·업로드 빈도·제목의 종목 언급률·쇼츠 비율을 재고 두 단계 규칙으로 걸렀습니다.</p></div></div>
          <div className="table-wrap" style={{ marginBottom: 12 }}><table>
            <thead><tr><th>단</th><th>구독자</th><th>언급률</th><th>뜻</th></tr></thead>
            <tbody>
              <tr><td><span className="chip accent">A</span></td><td>100만 이상</td><td>15% 이상</td><td className="muted" style={{ fontSize: 13 }}>시황이 섞여도 한 번의 언급이 닿는 사람이 많다</td></tr>
              <tr><td><span className="chip">B</span></td><td>주식 5만 · 코인 10만 이상</td><td>30% 이상</td><td className="muted" style={{ fontSize: 13 }}>규모는 작아도 제목에 종목을 콕 집는다</td></tr>
            </tbody>
          </table></div>
          <p className="muted" style={{ fontSize: 13, margin: 0 }}>공통: 45일 내 활동 · 쇼츠 50% 이하 · 방송사·증권사·거래소 공식 채널 제외. 구독자 373만 채널도 제목에 종목이 2%뿐이면 제외됐습니다.</p>
        </div>
        <div className="card col-6">
          <div className="card-head"><div><h3>매칭 규칙 (mentions/matcher.py)</h3><p>규칙마다 테스트가 있어 AI가 쓴 코드를 검증합니다.</p></div></div>
          <ul className="muted" style={{ paddingLeft: 18, margin: 0, fontSize: 13.5, lineHeight: 1.75 }}>
            <li>사전(이름·별칭)을 <b style={{ color: "var(--text)" }}>긴 표현부터</b> 정확 매칭. "삼성전자우"가 "삼성전자"보다 먼저, 잡힌 구간은 지워 중복 방지</li>
            <li>흔한 단어(삼성·현대·KT·은행…)는 단독 매칭 금지. "한국은행", "스트레스" 같은 표현은 먼저 지움</li>
            <li>자동 수집한 회사명은 <b style={{ color: "var(--text)" }}>한글 단어 경계</b>가 있어야 함(아스트라→아스트 ✗). 영문 티커 앞뒤에 한글이 붙으면 제외(SOL글로벌 ✗), 조사는 허용(BTC가 ✓)</li>
            <li>종목이 없어도 "반도체 급등"처럼 업종이 나오면 <Term k="theme">테마</Term> 사건으로 세고 대표 ETF로 잼</li>
            <li>자동 수집 코인(일반 단어 이름이 많음)은 코인 문맥이 있을 때만. 못 잡은 제목은 버리지 않고 남김</li>
          </ul>
        </div>

        <div className="card col-6">
          <div className="card-head"><div><h3>채널 목록</h3><p>구독자 순. 채널 페이지에서 언급 뒤 성적을 비교할 수 있습니다.</p></div></div>
          {loading ? <SkeletonRows n={8} /> : (
            <div className="table-wrap" style={{ maxHeight: 400, overflowY: "auto" }}><table>
              <thead><tr><th>채널</th><th>분류</th><th className="num">구독자</th></tr></thead>
              <tbody>{chList.map((c) => <tr key={c.channel_id}><td className="name"><b style={{ fontWeight: 600 }}>{c.title}</b><small>{c.handle}</small></td><td><span className={"chip " + (c.category === "crypto" ? "warn" : "accent")}>{c.category === "crypto" ? "코인" : "주식"}</span></td><td className="num">{compact(c.subscriber_count)}</td></tr>)}</tbody>
            </table></div>
          )}
        </div>
        <div className="card col-6">
          <div className="card-head"><div><h3>종목을 못 잡은 제목 (최근 20개)</h3><p><Term k="match">매칭 성공률</Term>의 반대편. 대부분 종목이 아니라 시황·거시 이야기이고, 종목이 있는데 놓친 것은 별칭 사전에 추가합니다.</p></div></div>
          {loading ? <SkeletonRows n={8} /> : (
            <ul style={{ paddingLeft: 18, margin: 0, fontSize: 13.5, lineHeight: 1.7, maxHeight: 400, overflowY: "auto" }}>
              {(un?.items || []).map((u) => <li key={u.video_id}>{u.title} <span className="muted">{dateOnly(u.published_at)}</span></li>)}
            </ul>
          )}
        </div>
        <div className="card col-12 flat">
          <div className="card-head"><div><h3>지키는 것</h3></div></div>
          <ul className="muted" style={{ paddingLeft: 18, margin: 0, fontSize: 13.5, lineHeight: 1.75 }}>
            <li>공개 메타데이터만 쓴다(제목·게시일·조회수). 자막·댓글은 수집하지 않는다.</li>
            <li>특정 종목을 추천하지 않는다. 통계와 <Term k="n">표본 수</Term>만 보여주고 30건 미만은 참고용으로 표시한다.</li>
            <li>채널 이름은 보여주되 "누가 틀렸나"가 아니라 "유튜브 언급을 따라가면 어떻게 되나"를 보는 학습용 통계임을 고지한다.</li>
          </ul>
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}

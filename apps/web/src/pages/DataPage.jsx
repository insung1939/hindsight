import { useEffect, useState } from "react";
import { api } from "../api";

// 수업 필수 페이지 — 수집한 데이터의 설명·출처·기초 통계. market-data 는 여기서만 읽는다.
const SOURCES = [
  ["국내 주식·ETF 일별 시세", "금융위원회_주식시세정보 · 공공데이터포털", "https://www.data.go.kr/data/15094808/openapi.do", "Open API (키)"],
  ["미국 ETF 일별 시세 · 환율 이력", "Yahoo Finance chart API", "https://finance.yahoo.com", "HTTP JSON (키 불필요)"],
  ["비트코인 일봉", "업비트 Open API · 두나무", "https://docs.upbit.com", "Open API (키 불필요)"],
  ["공식 고시환율", "환율 Open API · 한국수출입은행", "https://www.koreaexim.go.kr/ir/HPHKIR020M01", "Open API (키)"],
  ["배당 결정 공시", "DART OpenAPI · 금융감독원", "https://opendart.fss.or.kr", "Open API (키) · 6주차"],
  ["ETF 분배금", "운용사 상품 페이지 (TIGER·KODEX 등)", "", "크롤링 · 5주차"],
];

export default function DataPage() {
  const [assets, setAssets] = useState([]);
  const [stats, setStats] = useState({});
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const a = (await api("marketData", "/v1/assets")).items;
        setAssets(a);
        const s = {};
        await Promise.all(a.map(async (x) => {
          const p = (await api("marketData", `/v1/assets/${x.asset_id}/prices`, { params: { limit: 5000 } })).items;
          s[x.asset_id] = p.length ? { n: p.length, from: p[0].trade_date, to: p[p.length - 1].trade_date, last: p[p.length - 1].close } : { n: 0 };
        }));
        setStats(s);
      } catch (e) { setErr(e); }
    })();
  }, []);

  return (
    <div className="grid">
      <div className="card wide">
        <h2>데이터 출처</h2>
        <table>
          <thead><tr><th>데이터</th><th>명칭 · 기관</th><th>방식</th></tr></thead>
          <tbody>{SOURCES.map(([d, n, u, m]) => (
            <tr key={d}><td>{d}</td><td>{u ? <a href={u} target="_blank" rel="noreferrer">{n}</a> : n}</td><td>{m}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <div className="card wide">
        <h2>수집 현황 (market-data)</h2>
        {err && <div className="problem">{err.message}</div>}
        <table>
          <thead><tr><th>자산</th><th>시장</th><th>출처</th><th className="num">건수</th><th>기간</th><th className="num">최근 종가</th></tr></thead>
          <tbody>{assets.map((a) => {
            const s = stats[a.asset_id];
            return (
              <tr key={a.asset_id}>
                <td>{a.name}<div className="muted">{a.asset_id}</div></td>
                <td>{a.market}</td><td>{a.source}</td>
                <td className="num">{s ? s.n.toLocaleString() : "…"}</td>
                <td>{s?.n ? `${s.from} ~ ${s.to}` : <span className="muted">키 필요 / 미수집</span>}</td>
                <td className="num">{s?.n ? `${s.last.toLocaleString()} ${a.currency}` : ""}</td>
              </tr>
            );
          })}</tbody>
        </table>
        <p className="muted">시세는 매일 07:10 GitHub Actions 가 각 서비스의 /internal/sync 를 호출해 갱신합니다. 국내 시세와 공식 환율은 인증키 등록 후 수집됩니다.</p>
      </div>
    </div>
  );
}

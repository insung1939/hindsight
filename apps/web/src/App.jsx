import { useEffect, useState } from "react";
import { api } from "./api";
import ThisMonth from "./pages/ThisMonth";
import Assets from "./pages/Assets";
import TimeMachine from "./pages/TimeMachine";
import Myths from "./pages/Myths";
import DataPage from "./pages/DataPage";
import Setup from "./pages/Setup";
import "./App.css";

const TABS = [
  ["month", "이번 달"],
  ["assets", "자산 현황"],
  ["time", "타임머신"],
  ["myths", "신화 검증"],
  ["data", "데이터"],
];

export default function App() {
  const [tab, setTab] = useState("month");
  const [portfolios, setPortfolios] = useState(null);
  const [pid, setPid] = useState(null);
  const [error, setError] = useState(null);
  const [dark, setDark] = useState(() => window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  const loadPortfolios = async () => {
    try {
      const r = await api("portfolio", "/v1/portfolios");
      setPortfolios(r.items);
      if (r.items.length && !pid) setPid(r.items[0].id);
      setError(null);
    } catch (e) {
      setError(e);
      setPortfolios([]);
    }
  };
  useEffect(() => { loadPortfolios(); }, []);

  const portfolio = portfolios?.find((p) => p.id === pid);

  return (
    <div className={dark ? "app dark" : "app"}>
      <header className="top">
        <div>
          <h1>루틴</h1>
          <p className="tag">다자산 적립식 투자자의 운영 시스템 · 매달 무엇을 얼마 살지, 규칙을 지켰는지</p>
        </div>
        <div className="top-right">
          {portfolios?.length > 0 && (
            <select value={pid ?? ""} onChange={(e) => setPid(Number(e.target.value))}>
              {portfolios.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.owner})</option>)}
            </select>
          )}
          <button className="ghost" onClick={() => setDark(!dark)}>{dark ? "라이트" : "다크"}</button>
        </div>
      </header>

      {error && (
        <div className="problem">
          서버에 연결하지 못했습니다: {error.message}
          <span className="muted"> — Render 무료 플랜은 첫 요청에 30~60초 걸릴 수 있습니다. 잠시 후 새로고침.</span>
        </div>
      )}

      {portfolios && portfolios.length === 0 && !error && (
        <Setup onDone={loadPortfolios} />
      )}

      {portfolio && (
        <>
          <nav className="tabs">
            {TABS.map(([k, label]) => (
              <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>
            ))}
          </nav>
          <main>
            {tab === "month" && <ThisMonth portfolio={portfolio} />}
            {tab === "assets" && <Assets portfolio={portfolio} />}
            {tab === "time" && <TimeMachine portfolio={portfolio} />}
            {tab === "myths" && <Myths />}
            {tab === "data" && <DataPage />}
          </main>
        </>
      )}

      <footer className="muted">
        KAIST 디지털금융MBA 클라우드컴퓨팅실습 팀 프로젝트 · 정보 제공 목적이며 특정 종목을 추천하지 않습니다.
      </footer>
    </div>
  );
}

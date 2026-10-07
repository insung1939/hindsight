import { useEffect, useState } from "react";
import { onWaking } from "./api";
import Home from "./pages/Home";
import Analysis from "./pages/Analysis";
import Channels from "./pages/Channels";
import Ticker from "./pages/Ticker";
import DataPage from "./pages/DataPage";
import "./styles.css";

const TABS = [["home", "홈"], ["analysis", "언급 뒤에"], ["channels", "채널"], ["ticker", "종목"], ["data", "데이터"]];

// 해시 라우팅: #analysis, #ticker/KRX:005930 — 주소를 공유할 수 있고 새로고침해도 같은 화면
function parseHash() {
  const h = (location.hash || "#home").slice(1);
  const [tab, ...rest] = h.split("/");
  return { tab: TABS.some(([k]) => k === tab) ? tab : "home", arg: rest.length ? decodeURIComponent(rest.join("/")) : null };
}

export default function App() {
  const [route, setRoute] = useState(parseHash);
  const [waking, setWaking] = useState(null);
  useEffect(() => { const f = () => { setRoute(parseHash()); window.scrollTo({ top: 0 }); }; window.addEventListener("hashchange", f); return () => window.removeEventListener("hashchange", f); }, []);
  useEffect(() => onWaking(setWaking), []);
  const go = (tab, arg) => { location.hash = arg ? `${tab}/${encodeURIComponent(arg)}` : tab; };

  return (
    <>
      <header className="topbar">
        <div className="container">
          <a className="brand" href="#home"><span className="logo"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M4 17l5-6 4 3 7-9" /></svg></span>힌드사이트 <small>유튜버가 말한 종목, 그 뒤에</small></a>
          <nav className="nav">{TABS.map(([k, l]) => <a key={k} href={"#" + k} className={route.tab === k ? "on" : ""}>{l}</a>)}</nav>
        </div>
      </header>
      {waking?.waking && <div className="container"><div className="banner warn"><span className="spin" />서버를 깨우는 중입니다. 무료 서버는 15분 쉬면 잠들어 첫 응답에 30초쯤 걸립니다. 자동으로 다시 시도합니다… {waking.attempt}/4</div></div>}
      {waking?.failed && <div className="container"><div className="banner err">서버에 연결하지 못했습니다. 잠시 뒤 새로고침해 주세요.</div></div>}
      <main>
        {route.tab === "home" && <Home go={go} />}
        {route.tab === "analysis" && <Analysis go={go} />}
        {route.tab === "channels" && <Channels go={go} />}
        {route.tab === "ticker" && <Ticker assetId={route.arg} go={go} />}
        {route.tab === "data" && <DataPage />}
      </main>
      <footer>
        <div className="container">
          <span>힌드사이트 · KAIST 디지털금융MBA 클라우드컴퓨팅실습 5조 · 학습용 통계이며 투자 권유가 아닙니다</span>
          <span><a href="https://github.com/insung1939/hindsight" target="_blank" rel="noreferrer">GitHub</a> · <a href={(import.meta.env.VITE_API_URL || "http://localhost:8000") + "/docs"} target="_blank" rel="noreferrer">API 문서</a></span>
        </div>
      </footer>
    </>
  );
}

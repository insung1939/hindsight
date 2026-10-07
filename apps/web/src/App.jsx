import { useEffect, useState } from "react";
import { onWaking } from "./api";
import { LoadingBar } from "./components";
import Home from "./pages/Home";
import Analysis from "./pages/Analysis";
import Channels from "./pages/Channels";
import Ticker from "./pages/Ticker";
import DataPage from "./pages/DataPage";
import Channel from "./pages/Channel";
import "./styles.css";

const TABS = [["home", "홈"], ["analysis", "언급 뒤에"], ["channels", "채널"], ["ticker", "종목"], ["data", "데이터"], ["channel", null]];

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
      <LoadingBar />
      <header className="topbar">
        <div className="container">
          <a className="brand" href="#home"><img src="/logo.svg" alt="" width="28" height="28" style={{ borderRadius: 8 }} /><span className="wordmark">HINDSIGHT</span><small>유튜버가 오른다고 한 종목, 정말 올랐을까?</small></a>
          <nav className="nav">{TABS.filter(([, l]) => l).map(([k, l]) => <a key={k} href={"#" + k} className={route.tab === k || (k === "channels" && route.tab === "channel") ? "on" : ""}>{l}</a>)}</nav>
        </div>
      </header>
      {waking?.waking && <div className="container"><div className="banner warn"><span className="spin" />서버 깨우는 중 (무료 서버는 15분 쉬면 잠든다) · 다시 시도 {waking.attempt}/4</div></div>}
      {waking?.failed && <div className="container"><div className="banner err">서버 연결 실패. 잠시 뒤 새로고침.</div></div>}
      <main>
        {route.tab === "home" && <Home go={go} />}
        {route.tab === "analysis" && <Analysis go={go} />}
        {route.tab === "channels" && <Channels go={go} />}
        {route.tab === "ticker" && <Ticker assetId={route.arg} go={go} />}
        {route.tab === "data" && <DataPage />}
        {route.tab === "channel" && <Channel channelId={route.arg} go={go} />}
      </main>
      <footer>
        <div className="container">
          <span>HINDSIGHT · KAIST 디지털금융MBA 클라우드컴퓨팅실습 5조 · 학습용 통계, 투자 권유 아님</span>
          <span><a href="https://github.com/insung1939/hindsight" target="_blank" rel="noreferrer">GitHub</a> · <a href={(import.meta.env.VITE_API_URL || "http://localhost:8000") + "/docs"} target="_blank" rel="noreferrer">API 문서</a></span>
        </div>
      </footer>
    </>
  );
}

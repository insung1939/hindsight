import { useEffect, useState } from "react";
import { onWaking } from "./api";
import Trending from "./pages/Trending";
import Afterwards from "./pages/Afterwards";
import Timeline from "./pages/Timeline";
import DataPage from "./pages/DataPage";
import "./App.css";

const TABS = [
  ["trending", "이번 주 언급"],
  ["after", "언급 뒤에"],
  ["timeline", "종목 타임라인"],
  ["data", "데이터"],
];

export default function App() {
  const [tab, setTab] = useState("trending");
  const [asset, setAsset] = useState(null); // 타임라인으로 넘길 종목
  const [dark, setDark] = useState(() => window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  const [waking, setWaking] = useState(null);
  useEffect(() => onWaking(setWaking), []);
  const openTimeline = (assetId) => { setAsset(assetId); setTab("timeline"); };

  return (
    <div className={dark ? "app dark" : "app"}>
      <header className="top">
        <div>
          <h1>힌드사이트</h1>
          <p className="tag">유튜버가 말한 종목, 그 뒤에 어떻게 됐나 · 언급 뒤 5·20·60 거래일 수익률</p>
        </div>
        <button className="ghost" onClick={() => setDark(!dark)}>{dark ? "라이트" : "다크"}</button>
      </header>

      <nav className="tabs">
        {TABS.map(([k, label]) => (
          <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>
        ))}
      </nav>
      {waking?.waking && <div className="wake">서버를 깨우는 중입니다 (무료 서버는 15분 쉬면 잠듭니다). 자동으로 다시 시도합니다… {waking.attempt}/4</div>}
      {waking?.failed && <div className="problem">서버에 연결하지 못했습니다. 잠시 뒤 새로고침해 주세요.</div>}
      <main>
        {tab === "trending" && <Trending onPick={openTimeline} />}
        {tab === "after" && <Afterwards onPick={openTimeline} />}
        {tab === "timeline" && <Timeline assetId={asset} onChange={setAsset} />}
        {tab === "data" && <DataPage />}
      </main>

      <footer className="muted">
        KAIST 디지털금융MBA 클라우드컴퓨팅실습 팀 프로젝트 · 채널은 익명 집계 · 통계는 정보 제공 목적이며 특정 종목을 추천하지 않습니다.
      </footer>
    </div>
  );
}

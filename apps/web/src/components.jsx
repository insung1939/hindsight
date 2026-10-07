import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { onProgress } from "./api";

// ── 데이터 훅: 로딩 중에도 이전 데이터를 유지해 화면이 뚝 끊기지 않게 ──
export function useLoad(fn, deps) {
  const [state, set] = useState({ data: null, loading: true, error: null });
  useEffect(() => {
    let alive = true;
    set((s) => ({ ...s, loading: true, error: null }));
    fn().then((data) => alive && set({ data, loading: false, error: null }))
      .catch((error) => alive && set((s) => ({ data: s.data, loading: false, error })));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

// ── 용어 설명: 점선 밑줄 + 떠오르는 설명 ──
export const GLOSSARY = {
  mention: ["언급", "영상 제목에 종목 이름·별칭(삼전, 하닉, 엔비디아)이 나온 것."],
  stance: ["낙관 언급", "제목에 오른다·급등·매수·기회·목표가 같은 말이 있는 언급. 하락·폭락·매도·조심 같은 말이 더 많으면 제외. 이 서비스는 낙관 언급만 센다: 유튜브가 좋다고 한 종목이 실제로 올랐나."],
  t0: ["사건일(T0)", "영상을 보고 처음 거래할 수 있는 날. 국내 15:30 전 게시면 그날, 뒤면 다음 거래일. 미국 동부 16:00, 코인은 업비트 09:00 캔들."],
  horizon: ["5·20·60 거래일 수익률", "사건일 종가와 5거래일(1주)·20거래일(1개월)·60거래일(3개월) 뒤 종가를 비교한 변화율. 그 사이 일일 등락은 보지 않는다. 휴장일은 안 센다."],
  excess: ["시장 대비", "같은 기간 벤치마크(코스피·S&P500·비트코인) 수익률을 뺀 값. 시장이 더 올랐으면 음수."],
  win: ["상승 확률", "수익률이 0보다 큰 언급의 비율. 50%면 동전 던지기."],
  xwin: ["시장 이김", "시장 대비 수익률이 0보다 큰 비율."],
  awin: ["종목 승률", "채널이 언급한 종목 n개 중, 그 채널 언급 뒤 평균 수익률이 양(+)인 종목의 비중. 건 기준 상승 확률과 달리 종목을 한 표로 센다. 언급 종목 10개 이상만."],
  vol: ["거래량 비율", "언급 뒤 5일 평균 거래량 ÷ 언급 전 20일 평균. 1 미만이면 거래는 언급 전에 이미 몰렸다."],
  disc: ["공시 동반", "사건일 ±3일에 DART 주요 공시(실적·계약·자금조달·주요사항)가 있던 국내 언급의 비율."],
  n: ["표본", "기간이 지나 수익률이 계산된 언급 수. 30건 미만은 참고용."],
  surge: ["급증", "최근 N일 언급 ÷ 직전 N일 언급. 직전이 0이면 신규."],
  prev: ["직전", "바로 앞 같은 길이 기간의 언급 수. 7일이면 8~14일 전."],
  views: ["조회수", "그 기간에 이 종목을 언급한 영상들의 조회수 합(수집 시점)."],
  channels: ["채널 수", "그 기간에 이 종목을 언급한 채널 수."],
  past: ["과거 반응 (20일)", "이 종목이 전에 언급된 건마다 '사건일 종가 → 20거래일 뒤 종가' 수익률을 구해 평균한 값. n은 20거래일이 지나 계산이 끝난 언급 수. 일일 수익률 평균이 아니다."],
  theme: ["업종·테마", "'반도체 급등'처럼 종목 없이 업종만 말한 제목. 대표 ETF 수익률로 재고 종목과 섞지 않는다."],
  match: ["매칭 성공률", "제목에서 종목이나 테마를 하나라도 찾은 비율. 못 찾은 제목도 남겨 둔다."],
};
export function Term({ k, children }) {
  const [label, text] = GLOSSARY[k] || [k, ""];
  const ref = useRef(null);
  const [pos, setPos] = useState(null);
  const show = () => {
    const r = ref.current?.getBoundingClientRect(); if (!r) return;
    const w = Math.min(320, window.innerWidth - 24);
    setPos({ left: Math.max(12, Math.min(r.left, window.innerWidth - w - 12)), top: r.bottom + 8, w, above: r.bottom + 140 > window.innerHeight ? r.top : null });
  };
  return (
    <span ref={ref} className="term" tabIndex={0} onMouseEnter={show} onMouseLeave={() => setPos(null)} onFocus={show} onBlur={() => setPos(null)}>
      {children || label}
      {pos && createPortal(
        <span className="tip" role="tooltip" style={{ left: pos.left, width: pos.w, ...(pos.above != null ? { bottom: window.innerHeight - pos.above + 8 } : { top: pos.top }) }}>
          <b>{label}</b><br />{text}
        </span>, document.body)}
    </span>
  );
}

// 상단 로딩 바 — 요청이 하나라도 진행 중이면 흐른다
export function LoadingBar() {
  const [n, setN] = useState(0);
  useEffect(() => onProgress(setN), []);
  return <div className={"loadbar " + (n > 0 ? "on" : "")} aria-hidden />;
}

export function Stat({ k, label, value, sub, cls, loading }) {
  return (
    <div className="card stat">
      <span className="label">{k ? <Term k={k}>{label}</Term> : label}</span>
      {loading ? <span className="sk sk-big">0</span> : <span className={"value " + (cls || "")}>{value}</span>}
      {sub && <span className="sub">{loading ? <span className="sk sk-line" style={{ display: "inline-block", width: 160 }} /> : sub}</span>}
    </div>
  );
}

export function Seg({ value, onChange, options }) {
  return <div className="seg">{options.map(([v, l]) => <button key={v} className={v === value ? "on" : ""} onClick={() => onChange(v)}>{l}</button>)}</div>;
}

export function SkeletonRows({ n = 6 }) {
  return <div>{Array.from({ length: n }).map((_, i) => <div key={i} className="sk sk-row" />)}</div>;
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return <div className="banner err">⚠ {error.message}{error.status ? <span className="muted"> (HTTP {error.status})</span> : null}</div>;
}

export function Histogram({ hist, loading }) {
  if (loading && !hist) return <div className="sk" style={{ height: 170 }} />;
  if (!hist) return null;
  const max = Math.max(1, ...hist.map((b) => b.n));
  const label = (b) => (b.from <= -1 ? "< −20%" : b.to >= 9 ? "> +20%" : `${Math.round(b.from * 100)}~${Math.round(b.to * 100)}%`);
  return (
    <div className="hist">
      {hist.map((b, i) => (
        <div key={i} className="c" title={`${label(b)}: ${b.n.toLocaleString()}건`}>
          <div className="n">{b.n.toLocaleString()}</div>
          <div className={"b " + (b.from >= 0 ? "up" : "")} style={{ height: `${(b.n / max) * 100}%` }} />
          <div className="l">{label(b)}</div>
        </div>
      ))}
    </div>
  );
}

export function Disclaimer() {
  return <p className="disclaimer">학습용 통계. 투자 권유 아님. 제목만 보고 언급을 셌고 영상의 방향(매수·매도)은 가리지 않았다.</p>;
}

import { useEffect, useState } from "react";

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
  mention: ["언급", "유튜브 영상 제목에 종목 이름이나 별칭(삼전, 하닉, 엔비디아…)이 등장한 것. 영상 하나에 여러 종목이 있을 수 있고, '사라'인지 '조심하라'인지는 판단하지 않습니다."],
  t0: ["사건일(T0)", "영상을 보고 처음 거래할 수 있는 날의 종가를 기준점으로 씁니다. 국내는 15:30 전 게시면 그날, 뒤면 다음 거래일. 미국은 동부 16:00, 코인은 업비트 일봉(09:00) 기준."],
  horizon: ["5·20·60 거래일 수익률", "사건일 종가 대비 5거래일(약 1주), 20거래일(약 1개월), 60거래일(약 3개월) 뒤 종가의 변화율입니다. 주말·휴장일은 세지 않습니다."],
  excess: ["초과수익 (시장 대비)", "같은 기간 벤치마크 수익률을 뺀 값입니다. 국내는 코스피, 미국은 S&P500, 코인은 비트코인. 종목이 올랐어도 시장이 더 올랐으면 음수입니다."],
  win: ["상승 확률", "기간이 지난 언급 가운데 수익률이 0보다 큰 비율. 50%면 동전 던지기와 같습니다."],
  xwin: ["시장을 이긴 비율", "초과수익이 0보다 큰 언급의 비율."],
  vol: ["거래량 비율", "언급 뒤 5거래일 평균 거래량 ÷ 언급 전 20거래일 평균 거래량. 1보다 크면 언급 뒤에 거래가 늘었고, 1보다 작으면 언급 전에 이미 거래가 몰렸다는 뜻입니다."],
  disc: ["주요 공시 동반", "사건일 앞뒤 3일 안에 DART 주요 공시(실적·계약·자금조달·주요사항)가 있었던 국내 종목 언급의 비율. 유튜브 언급이 공시를 따라 나온 해설인지 가늠합니다."],
  n: ["표본 (n)", "기간이 지나 수익률이 계산된 언급 수. 30건 미만이면 참고용으로만 보세요."],
  surge: ["급증 배수", "최근 N일 언급 수 ÷ 직전 N일 언급 수. 직전이 0이면 '신규'로 표시합니다."],
  prev: ["직전", "선택한 기간 바로 앞 같은 길이의 기간에 있었던 언급 수. 7일을 골랐으면 8~14일 전."],
  views: ["조회수", "최근 N일 안에 이 종목을 언급한 영상들의 조회수 합계(수집 시점 기준). 채널 수와 함께 얼마나 널리 들렸는지를 봅니다."],
  channels: ["채널 수", "그 기간에 이 종목을 한 번이라도 언급한 채널의 수. 한 채널이 여러 번 말한 것과 여러 채널이 말한 것을 구분합니다."],
  past: ["과거 반응", "이 종목이 이전에 언급됐을 때 20거래일 뒤 평균 수익률. '전에 떴을 때 어땠나'를 보여주며, 표본이 적으면 참고용입니다."],
  theme: ["업종·테마", "'반도체 급등', '코스피 폭락'처럼 종목 없이 업종만 말한 제목도 사건으로 세고, 대표 ETF(KODEX 반도체 등)의 수익률로 잽니다. 종목 통계와 섞지 않습니다."],
  match: ["매칭 성공률", "수집한 영상 제목 가운데 종목이나 테마를 하나라도 찾아낸 비율. 못 찾은 제목도 버리지 않고 남겨 사전 보강에 씁니다."],
};
export function Term({ k, children }) {
  const [label, text] = GLOSSARY[k] || [k, ""];
  return (
    <span className="term" tabIndex={0}>{children || label}<span className="tip" role="tooltip"><b>{label}</b> — {text}</span></span>
  );
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
  return <p className="disclaimer">이 통계는 학습용이며 투자 권유가 아닙니다. 영상 제목만 보고 '언급'을 셌을 뿐, 영상이 사라고 했는지 조심하라고 했는지는 구분하지 않습니다.</p>;
}

import { useEffect, useState } from "react";
import { api, krw, pct } from "../api";

export default function Assets({ portfolio }) {
  const [v, setV] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    api("portfolio", `/v1/portfolios/${portfolio.id}/valuation`).then(setV).catch(setErr);
  }, [portfolio.id]);

  if (err) return <div className="problem">{err.message}</div>;
  if (!v) return <p className="muted">평가 중… (portfolio → market-data)</p>;
  return (
    <div className="grid">
      <div className="card">
        <h3>총 평가액 · {v.as_of}</h3>
        <div className="big">{krw(v.total_value_krw)}</div>
        {v.warnings.map((w, i) => <p key={i} className="warn" style={{ fontSize: 13 }}>{w}</p>)}
      </div>
      <div className="card wide">
        <h3>자산별 비중 (원화 환산)</h3>
        <table>
          <thead><tr><th>자산</th><th className="num">수량</th><th className="num">가격</th><th className="num">환율</th><th className="num">평가액</th><th className="num">비중 / 목표</th></tr></thead>
          <tbody>
            {v.items.map((it) => (
              <tr key={it.holding_id}>
                <td>{it.asset_id}<div className="muted">{it.price_date}</div></td>
                <td className="num">{it.quantity}</td>
                <td className="num">{it.price.toLocaleString()} {it.currency}</td>
                <td className="num">{it.fx_rate.toLocaleString()}</td>
                <td className="num">{krw(it.value_krw)}</td>
                <td className="num">
                  <span className={Math.abs(it.weight - it.target_weight) > 0.05 ? "warn" : "good"}>{pct(it.weight)}</span> / {pct(it.target_weight, 0)}
                </td>
              </tr>
            ))}
            {v.items.length === 0 && <tr><td colSpan="6" className="muted">보유 종목이 없습니다. 이번 달 지시서를 실행하면 여기에 쌓입니다.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { api, assetNames, channelMap, compact, dateOnly, num, pct, pct0, sign, MARKET_LABEL } from "../api";
import { Disclaimer, ErrorBox, SkeletonRows, Stat, Term, useLoad } from "../components";

// 채널 하나 — 오른다고 한 언급과 그 뒤 성적
export default function Channel({ channelId, go }) {
  const data = useLoad(async () => {
    const [chs, names, ev, sum] = await Promise.all([channelMap(), assetNames(), api("stats", `/v1/channels/${channelId}/events`),
      api("stats", "/v1/summary", { params: { scope: `channel:${channelId}`, horizon: 20, stance: "bull" }, ttl: 5 * 60e3 }).then((r) => r.value).catch(() => null)]);
    return { ch: chs[channelId], names, events: ev.items.filter((e) => e.stance === "bull"), all: ev.items.length, sum };
  }, [channelId]);
  const d = data.data; const ch = d?.ch; const sum = d?.sum;
  const byAsset = {};
  (d?.events || []).forEach((e) => { const a = byAsset[e.asset_id] || (byAsset[e.asset_id] = { id: e.asset_id, n: 0, r: [] }); a.n++; if (e.r20 != null) a.r.push(e.r20); });
  const assets = Object.values(byAsset).map((a) => ({ ...a, mean: a.r.length ? a.r.reduce((x, y) => x + y, 0) / a.r.length : null, up: a.r.filter((x) => x > 0).length })).sort((a, b) => b.n - a.n).slice(0, 30);
  const yt = ch?.handle ? `https://www.youtube.com/${ch.handle}` : null;

  return (
    <div className="page container">
      <div className="page-head">
        <div className="eyebrow"><a href="#channels" style={{ color: "var(--accent)" }}>채널</a> › 상세</div>
        <h1>{ch?.title || (data.loading ? "…" : channelId)}</h1>
        <p>{ch ? `${ch.handle} · ${ch.category === "crypto" ? "코인" : "주식"} · 구독자 ${compact(ch.subscriber_count)}` : ""}{yt && <> · <a href={yt} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>YouTube 채널 열기 ↗</a></>}</p>
      </div>
      <ErrorBox error={data.error} />
      <div className="grid">
        <div className="col-3"><Stat k="stance" label="오른다고 한 언급" loading={data.loading && !d} value={d ? `${num(d.events.length)}건` : "—"} sub={d ? `종목 나온 영상 ${num(d.all)}건 중 · 최근 1년` : ""} /></div>
        <div className="col-3"><Stat k="past" label="언급 뒤 20거래일 수익률 평균" loading={data.loading && !d} value={pct(sum?.mean)} cls={sign(sum?.mean)} sub={sum?.n ? `n=${num(sum.n)}${sum.low_sample ? " · 참고용" : ""}` : "계산 전"} /></div>
        <div className="col-3"><Stat k="win" label="20거래일 뒤 오른 비율" loading={data.loading && !d} value={pct0(sum?.win_rate)} sub={sum ? `시장 대비 ${pct(sum.excess_mean)}` : ""} /></div>
        <div className="col-3"><Stat k="awin" label="종목 승률" loading={data.loading && !d} value={sum?.assets_n ? pct0(sum.asset_win_rate) : "—"} sub={sum?.assets_n ? `종목 ${sum.assets_n}개 중 ${sum.assets_up}개 상승` : "언급 종목 10개 미만"} /></div>
        <div className="card col-12">
          <div className="card-head"><div><h3>이 채널이 오른다고 한 종목 · 많이 말한 순</h3><p>종목을 누르면 주가 위 언급 시점을 본다</p></div></div>
          {data.loading && !d ? <SkeletonRows n={8} /> : (
            <div className="table-wrap" style={{ maxHeight: 480, overflowY: "auto" }}><table>
              <thead><tr><th>종목</th><th className="num">언급</th><th className="num"><Term k="past">20일 평균</Term></th><th className="num">오른 건</th><th>마지막 언급</th></tr></thead>
              <tbody>{assets.map((a) => { const nm = d.names[a.id]; const last = d.events.filter((e) => e.asset_id === a.id).map((e) => e.published_at).sort().pop(); return (
                <tr key={a.id} className="clickable" onClick={() => go("ticker", a.id)}>
                  <td className="name"><b>{nm?.name || a.id}</b><small>{nm?.asset_type === "theme" ? "업종·테마" : MARKET_LABEL[nm?.market] || ""} · {a.id.split(":")[1]}</small></td>
                  <td className="num">{a.n}</td><td className={"num " + sign(a.mean)}>{pct(a.mean)}</td><td className="num">{a.r.length ? `${a.up}/${a.r.length}` : "—"}</td><td className="muted">{dateOnly(last)}</td>
                </tr>); })}</tbody>
            </table></div>
          )}
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}

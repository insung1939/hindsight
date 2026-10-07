"""scripts/channels.json(discover_channels.py 결과)의 채널을 youtube 서비스에 등록한다. 핸들 → API 로 id 조회(채널당 1 유닛).
    .venv/bin/python scripts/register_channels.py [--base http://127.0.0.1:8002]"""
import argparse
import json
import os
from pathlib import Path

import httpx

ap = argparse.ArgumentParser()
ap.add_argument("--base", default=os.getenv("YOUTUBE_URL", "http://127.0.0.1:8002"))
a = ap.parse_args()
c = httpx.Client(timeout=60, headers={"X-Internal-Token": os.getenv("INTERNAL_TOKEN", "dev-token")})
rows = json.loads((Path(__file__).parent / "channels.json").read_text())
# A단(대형) 먼저, 그다음 주식 → 코인, 구독자 순. 익명 코드가 이 순서로 붙는다.
rows.sort(key=lambda r: (r["tier"], r["category"], -r["subscribers"]))
ok = dup = fail = 0
for r in rows:
    resp = c.post(f"{a.base}/v1/channels", json={"handle": r["handle"], "category": r["category"]})
    if resp.status_code == 201:
        ok += 1; print(f"  {resp.json()['anon_code']:>3} ← {r['title']}")
    elif resp.status_code == 409:
        dup += 1
    else:
        fail += 1; print(f"  !! {r['handle']} {resp.status_code} {resp.text[:120]}")
print(f"등록 {ok} · 이미 있음 {dup} · 실패 {fail}")

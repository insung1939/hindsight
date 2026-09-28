"""각 서비스의 FastAPI 앱에서 OpenAPI 를 뽑아 contracts/<service>.yaml 로 쓴다.

용도는 두 가지다.
 1) 최초 부트스트랩 — 명세 파일을 처음 만들 때.
 2) 구현을 바꾼 뒤 명세를 갱신할 때. 단, 규약상 순서는 '명세 수정 → PR(Spectral·oasdiff) → 구현' 이다.
    이 스크립트로 명세를 덮어쓰면 그 diff 가 곧 PR 리뷰 대상이 된다.

실행: python scripts/export_contracts.py [service ...]
"""
import importlib
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ["market-data", "youtube", "mentions", "stats"]


def export(service: str) -> Path:
    svc_dir = ROOT / "services" / service
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    sys.path.insert(0, str(svc_dir))
    for m in ("main", "models", "collectors", "seed", "engine", "matcher"):
        sys.modules.pop(m, None)
    app = importlib.import_module("main").app
    spec = app.openapi()
    spec["servers"] = [
        {"url": f"http://localhost:{8000 + SERVICES.index(service) + 1}", "description": "로컬"},
        {"url": f"https://hindsight-{service}.onrender.com", "description": "Render (팀 운영)"},
    ]
    out = ROOT / "contracts" / f"{service}.yaml"
    out.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    sys.path.remove(str(svc_dir))
    return out


if __name__ == "__main__":
    targets = sys.argv[1:] or SERVICES
    for s in targets:
        print("wrote", export(s).relative_to(ROOT))

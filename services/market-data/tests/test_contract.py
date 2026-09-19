"""계약 드리프트 검사 — contracts/<service>.yaml 의 경로·메서드 집합과 실제 앱이 같아야 한다.
명세를 먼저 고치고(API-First) 구현을 맞추는 순서를 CI 가 강제한다."""
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from main import app

SERVICE = Path(__file__).resolve().parents[1].name
CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / f"{SERVICE}.yaml"
METHODS = {"get", "post", "put", "patch", "delete"}


def _ops(paths: dict) -> set[tuple[str, str]]:
    return {(p, m) for p, item in paths.items() for m in item if m in METHODS}


def test_paths_match_contract():
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    expected = _ops(spec["paths"])
    actual = _ops(app.openapi()["paths"])
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"명세에는 있는데 구현이 없음: {sorted(missing)}"
    assert not extra, f"구현에는 있는데 명세에 없음(contracts/{SERVICE}.yaml 에 먼저 추가): {sorted(extra)}"


def test_healthz_and_problem_json():
    c = TestClient(app)
    assert c.get("/healthz").json()["status"] == "ok"
    r = c.get("/v1/definitely-not-a-route")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert "X-Request-ID" in r.headers

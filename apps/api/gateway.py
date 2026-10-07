"""합본 게이트웨이 — 수업 제출용 배포(Render 무료 웹 서비스 1개).

서비스 4개는 코드·DB 스키마를 그대로 둔 채 같은 컨테이너 안에서 각자 포트로 돌고(launcher.py),
이 앱이 하나의 주소에서 경로 접두사로 넘겨준다.

    /market-data/...  → 127.0.0.1:8001       /youtube/...  → 8002
    /mentions/...     → 8003                 /stats/...    → 8004
    /docs · /openapi.json  네 서비스 명세를 합친 Swagger 하나
    /healthz               네 서비스 상태 묶음

서비스 간 호출(mentions→youtube 등)은 컨테이너 안에서 직접 포트로 한다. 세미나용 분리 배포(k8s·APISIX)는 platform/ 에 그대로 있다.
"""
import asyncio
import copy
import os
import re

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

SERVICES = {"market-data": 8001, "youtube": 8002, "mentions": 8003, "stats": 8004}
HOP = {"host", "content-length", "transfer-encoding", "connection", "keep-alive", "te", "trailer", "upgrade", "proxy-authorization", "proxy-authenticate"}
PUBLIC_URL = os.getenv("PUBLIC_URL", "")  # 예: https://hindsight-api.onrender.com (없으면 상대 경로)

app = FastAPI(title="힌드사이트 API", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None,
              description="유튜버가 말한 종목, 그 뒤에 어떻게 됐나 — market-data · youtube · mentions · stats 네 서비스를 한 주소로 묶은 게이트웨이.")
client = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=5.0))


def upstream(svc: str) -> str:
    return f"http://127.0.0.1:{SERVICES[svc]}"


@app.get("/", include_in_schema=False)
def index():
    base = PUBLIC_URL
    return {"service": "hindsight", "docs": f"{base}/docs", "healthz": f"{base}/healthz",
            "services": {s: f"{base}/{s}" for s in SERVICES}, "per_service_docs": {s: f"{base}/{s}/docs" for s in SERVICES},
            "github": "https://github.com/insung1939/hindsight"}


@app.get("/healthz", include_in_schema=False)
async def healthz():
    async def one(svc):
        try:
            r = await client.get(f"{upstream(svc)}/healthz", timeout=5)
            return svc, r.json()
        except Exception as e:  # noqa: BLE001
            return svc, {"status": "down", "error": str(e)[:100]}
    results = dict(await asyncio.gather(*(one(s) for s in SERVICES)))
    ok = all(v.get("status") == "ok" for v in results.values())
    return JSONResponse({"status": "ok" if ok else "degraded", "services": results}, status_code=200 if ok else 503)


# ── 합친 OpenAPI ────────────────────────────────────────
_merged: dict | None = None


def _prefix_refs(obj, svc: str):
    """components.schemas 이름이 서비스끼리 겹치므로(ListChannels 등) '<svc>.' 접두사를 붙이고 $ref 를 고쳐 쓴다."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/components/schemas/"):
                name = v.rsplit("/", 1)[1]
                obj[k] = f"#/components/schemas/{svc}.{name}" if name != "Problem" else v
            else:
                _prefix_refs(v, svc)
    elif isinstance(obj, list):
        for v in obj:
            _prefix_refs(v, svc)


async def merged_openapi() -> dict:
    global _merged
    if _merged:
        return _merged
    out = {"openapi": "3.1.0",
           "info": {"title": "힌드사이트 API (합본)", "version": "1.0.0",
                    "description": "네 서비스의 명세를 경로 접두사로 합쳤다. 원본 명세는 contracts/<service>.yaml, 서비스별 Swagger 는 /<service>/docs."},
           "servers": [{"url": PUBLIC_URL or "/"}], "paths": {}, "components": {"schemas": {}}, "tags": []}
    for svc in SERVICES:
        try:
            r = await client.get(f"{upstream(svc)}/openapi.json", timeout=10)
            spec = r.json()
        except Exception:  # noqa: BLE001
            continue
        spec = copy.deepcopy(spec)
        _prefix_refs(spec, svc)
        for name, schema in spec.get("components", {}).get("schemas", {}).items():
            out["components"]["schemas"][name if name == "Problem" else f"{svc}.{name}"] = schema
        for path, item in spec.get("paths", {}).items():
            for op in item.values():
                if isinstance(op, dict):
                    op["tags"] = [f"{svc} · {t}" for t in op.get("tags", ["default"])]
                    if "operationId" in op:
                        op["operationId"] = f"{svc}_{op['operationId']}"
            out["paths"][f"/{svc}{path}"] = item
    tags = sorted({t for item in out["paths"].values() for op in item.values() if isinstance(op, dict) for t in op.get("tags", [])})
    out["tags"] = [{"name": t} for t in tags]
    if out["paths"]:
        _merged = out
    return out


@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    return await merged_openapi()


@app.get("/docs", include_in_schema=False)
async def docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="힌드사이트 API — Swagger UI",
                               swagger_ui_parameters={"docExpansion": "list", "defaultModelsExpandDepth": -1})


# ── 프록시 ──────────────────────────────────────────────
@app.api_route("/{svc}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], include_in_schema=False)
async def proxy(svc: str, path: str, request: Request):
    if svc not in SERVICES:
        return JSONResponse({"type": "about:blank", "title": "Not Found", "status": 404, "detail": f"서비스 {svc} 없음. 가능: {', '.join(SERVICES)}"},
                            status_code=404, media_type="application/problem+json")
    url = f"{upstream(svc)}/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP}
    headers["x-forwarded-prefix"] = f"/{svc}"
    body = await request.body()
    try:
        r = await client.request(request.method, url, params=request.query_params, headers=headers, content=body)
    except httpx.ConnectError:
        return JSONResponse({"type": "about:blank", "title": "Bad Gateway", "status": 502, "detail": f"{svc} 가 아직 기동 중"},
                            status_code=502, media_type="application/problem+json")
    resp_headers = {k: v for k, v in r.headers.items() if k.lower() not in HOP}
    content = r.content
    if path == "openapi.json" and r.status_code == 200:  # 서비스 자체 Swagger 의 "Try it out" 이 접두사를 타게
        spec = r.json()
        spec["servers"] = [{"url": f"{PUBLIC_URL}/{svc}"}]
        return JSONResponse(spec, headers={k: v for k, v in resp_headers.items() if k.lower() != "content-type"})
    if path == "docs" and r.status_code == 200:  # 서비스 Swagger 페이지의 /openapi.json 상대 경로 보정
        html = content.decode("utf-8")
        html = re.sub(r"url:\s*'/openapi\.json'", f"url: '/{svc}/openapi.json'", html)
        html = html.replace("'/openapi.json'", f"'/{svc}/openapi.json'").replace('"/openapi.json"', f'"/{svc}/openapi.json"')
        return Response(html, status_code=200, media_type="text/html")
    return Response(content, status_code=r.status_code, headers=resp_headers)

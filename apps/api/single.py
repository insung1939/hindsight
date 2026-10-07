"""합본 앱 — 서비스 4개를 **한 프로세스**에 마운트한다 (Render 무료 512MB 대비).

프로세스 5개(서비스 4 + 게이트웨이)로 띄우면 FastAPI·SQLAlchemy 를 다섯 번 올려 기본 메모리만 350MB 를 썼다.
여기서는 라이브러리를 한 번만 올리고, 각 서비스의 FastAPI 앱을 경로 접두사로 마운트한다. 코드는 services/<svc>/ 그대로다.

    /market-data/...  /youtube/...  /mentions/...  /stats/...   ← 각 서비스 앱 (자기 CORS·오류 포맷·/docs 유지)
    /docs · /openapi.json                                        ← 네 명세를 합친 Swagger 하나
    /healthz                                                     ← 네 서비스 상태 묶음

서비스 간 호출(mentions→youtube 등)은 여전히 REST 다. 주소만 자기 자신(http://127.0.0.1:$PORT/<svc>)을 가리킨다.
각 서비스의 main.py 가 `from models import …` 처럼 짧은 이름을 쓰므로, 하나를 import 한 뒤 그 이름들을 sys.modules 에서 치워
다음 서비스가 자기 것을 다시 import 하게 한다(이미 import 된 쪽은 자기 모듈 객체를 계속 참조한다).
"""
import copy
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ["market-data", "youtube", "mentions", "stats"]
LOCAL_MODULES = ("main", "models", "collectors", "seed", "matcher", "engine")
PORT = os.getenv("PORT", "8000")


def _load_env(svc_dir: Path) -> None:
    """로컬 실행용: services/<svc>/.env 를 읽어 없는 변수만 채운다 (배포는 플랫폼이 주입)."""
    f = svc_dir / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# 서비스 간 주소는 자기 자신. 사용자가 따로 지정했으면 그대로 둔다.
for svc in SERVICES:
    os.environ.setdefault(svc.upper().replace("-", "_") + "_URL", f"http://127.0.0.1:{PORT}/{svc}")
for svc in SERVICES:
    _load_env(ROOT / "services" / svc)

from fastapi import FastAPI, Request  # noqa: E402  (환경변수 세팅 뒤에 import — hs_common 이 import 시점에 .env 를 읽는다)
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.openapi.docs import get_swagger_ui_html  # noqa: E402

apps: dict[str, FastAPI] = {}
for svc in SERVICES:
    svc_dir = str(ROOT / "services" / svc)
    sys.path.insert(0, svc_dir)
    for m in LOCAL_MODULES:
        sys.modules.pop(m, None)
    apps[svc] = importlib.import_module("main").app
    sys.path.remove(svc_dir)
for m in LOCAL_MODULES:  # 마지막 서비스의 짧은 이름이 남지 않게
    sys.modules.pop(m, None)

app = FastAPI(title="힌드사이트 API", version="1.3.0", docs_url=None, redoc_url=None, openapi_url=None,
              description="유튜버가 말한 종목, 그 뒤에 어떻게 됐나 — market-data · youtube · mentions · stats 네 서비스를 한 프로세스·한 주소로.")
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET"], allow_headers=["*"])
for svc, sub in apps.items():
    app.mount(f"/{svc}", sub)


@app.on_event("startup")
def _startup():
    # 마운트된 앱의 startup(테이블 생성·시드)은 Starlette 가 자동으로 부르지 않으므로 직접 부른다
    for sub in apps.values():
        for handler in sub.router.on_startup:
            handler()


def public_base(request: Request) -> str:
    host = request.headers.get("host") or request.url.netloc
    return f"{request.url.scheme}://{host}"


@app.get("/", include_in_schema=False)
def index(request: Request):
    base = public_base(request)
    return {"service": "hindsight", "version": app.version, "mode": "single-process", "docs": f"{base}/docs", "healthz": f"{base}/healthz",
            "services": {s: f"{base}/{s}" for s in SERVICES}, "per_service_docs": {s: f"{base}/{s}/docs" for s in SERVICES},
            "github": "https://github.com/insung1939/hindsight"}


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok", "mode": "single-process", "services": {s: {"status": "ok", "service": s, "version": sub.version} for s, sub in apps.items()}}


def _prefix_refs(obj, svc: str):
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


_merged: dict | None = None


def merged_openapi() -> dict:
    global _merged
    if _merged:
        return _merged
    out = {"openapi": "3.1.0",
           "info": {"title": "힌드사이트 API (합본)", "version": app.version,
                    "description": "네 서비스의 명세를 경로 접두사로 합쳤다. 원본 명세는 contracts/<service>.yaml, 서비스별 Swagger 는 /<service>/docs."},
           "paths": {}, "components": {"schemas": {}}, "tags": []}
    for svc, sub in apps.items():
        spec = copy.deepcopy(sub.openapi())
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
    out["tags"] = [{"name": t} for t in sorted({t for item in out["paths"].values() for op in item.values() if isinstance(op, dict) for t in op.get("tags", [])})]
    _merged = out
    return out


@app.get("/openapi.json", include_in_schema=False)
def openapi_json(request: Request):
    return {**merged_openapi(), "servers": [{"url": public_base(request)}]}


@app.get("/docs", include_in_schema=False)
def docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="힌드사이트 API — Swagger UI",
                               swagger_ui_parameters={"docExpansion": "list", "defaultModelsExpandDepth": -1})

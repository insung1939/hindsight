"""서비스 공통 골격: CORS, 요청 ID, Problem 오류, /healthz, 내부 토큰 검사, (선택) OpenTelemetry."""
from fastapi import Depends, FastAPI, Header, HTTPException

from .errors import install_error_handlers
from .request_id import RequestIdMiddleware
from .settings import allowed_origins, env

try:  # 5주차: OTEL_EXPORTER_OTLP_ENDPOINT 가 있을 때만 켠다. 패키지가 없어도 서비스는 돈다.
    from .telemetry import setup_telemetry
except Exception:  # pragma: no cover
    setup_telemetry = None


def create_app(service_name: str, title: str, version: str, description: str = "") -> FastAPI:
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title=title, version=version, description=description,
                  contact={"name": f"{service_name} owner", "url": "https://github.com/insung1939/routine"})
    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(), allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID"])
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    @app.get("/healthz", tags=["ops"], operation_id="healthz", summary="서비스 상태")
    def healthz():
        return {"status": "ok", "service": service_name, "version": version}

    if setup_telemetry and env("OTEL_EXPORTER_OTLP_ENDPOINT"):
        setup_telemetry(app, service_name)
    _install_openapi_conventions(app, service_name)
    return app


def _install_openapi_conventions(app: FastAPI, service_name: str) -> None:
    """생성되는 OpenAPI 를 전사 규약에 맞춘다: 오류 응답은 전부 application/problem+json, info 에 x-owner.
    contracts/<service>.yaml 은 이 결과를 내보낸 것이고, Spectral 이 그 파일을 검사한다."""
    from .errors import PROBLEM, PROBLEM_SCHEMA

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = FastAPI.openapi(app)
        schema["openapi"] = "3.1.0"
        schema["info"]["x-owner"] = env("SERVICE_OWNER", f"team-{service_name}")
        schema["info"]["x-service"] = service_name
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas["Problem"] = PROBLEM_SCHEMA
        schemas.pop("HTTPValidationError", None)  # 422 도 Problem 으로 통일했으므로 불필요
        schemas.pop("ValidationError", None)
        tags = sorted({t for item in schema["paths"].values() for op in item.values()
                       if isinstance(op, dict) for t in op.get("tags", [])})
        schema["tags"] = [{"name": t} for t in tags]
        problem_content = {PROBLEM: {"schema": {"$ref": "#/components/schemas/Problem"}}}
        for path, item in schema["paths"].items():
            for method, op in item.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                responses = op.setdefault("responses", {})
                for code, resp in list(responses.items()):
                    if str(code)[0] in "45":
                        resp["content"] = problem_content
                if not path.startswith("/healthz"):
                    responses.setdefault("500", {"description": "서버 내부 오류", "content": problem_content})
                    if "{" in path:
                        responses.setdefault("404", {"description": "대상 없음", "content": problem_content})
                op.setdefault("parameters", []).append({
                    "name": "X-Request-ID", "in": "header", "required": False,
                    "schema": {"type": "string"}, "description": "요청 추적 ID. 없으면 서버가 만들어 응답 헤더로 돌려준다."})
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi


def internal_only(x_internal_token: str | None = Header(default=None, alias="X-Internal-Token")) -> None:
    """/internal/* 는 수집 스케줄러나 운영자만 부른다. INTERNAL_TOKEN 이 설정돼 있으면 검사한다."""
    expected = env("INTERNAL_TOKEN")
    if expected and x_internal_token != expected:
        raise HTTPException(401, "내부 토큰이 필요합니다.")


InternalOnly = Depends(internal_only)

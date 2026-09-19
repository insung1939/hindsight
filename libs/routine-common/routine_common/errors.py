"""RFC 9457 Problem Details. 모든 서비스가 같은 오류 모양을 돌려주게 한다."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM = "application/problem+json"
_TITLES = {400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
           409: "Conflict", 422: "Unprocessable Content", 500: "Internal Server Error",
           502: "Bad Gateway", 503: "Service Unavailable"}


def problem(status: int, detail: str, request: Request, type_: str = "about:blank", **extra) -> JSONResponse:
    body = {"type": type_, "title": _TITLES.get(status, "Error"), "status": status,
            "detail": detail, "instance": str(request.url.path)}
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return problem(exc.status_code, str(exc.detail), request)

    @app.exception_handler(HTTPException)
    async def _fastapi_http(request: Request, exc: HTTPException):
        return problem(exc.status_code, str(exc.detail), request)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return problem(422, "요청 값이 규격에 맞지 않습니다.", request, errors=exc.errors())

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        return problem(500, "서버 내부 오류", request)


PROBLEM_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"}, "title": {"type": "string"},
        "status": {"type": "integer"}, "detail": {"type": "string"}, "instance": {"type": "string"},
    },
    "required": ["type", "title", "status"],
}

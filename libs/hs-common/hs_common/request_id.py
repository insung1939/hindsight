import contextvars
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

HEADER = "X-Request-ID"
current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """요청마다 X-Request-ID 를 받거나 만들어서 응답과 하위 호출에 전파한다. 트레이스 연결의 기본 단위."""

    async def dispatch(self, request, call_next):
        rid = request.headers.get(HEADER) or uuid.uuid4().hex
        token = current_request_id.set(rid)
        try:
            response = await call_next(request)
        finally:
            current_request_id.reset(token)
        response.headers[HEADER] = rid
        return response

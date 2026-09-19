"""서비스 간 호출 클라이언트. X-Request-ID 를 전파하고 실패를 502/504 Problem 으로 바꾼다."""
import httpx
from fastapi import HTTPException

from .request_id import HEADER, current_request_id
from .settings import service_url


class ServiceClient:
    def __init__(self, name: str, timeout: float = 10.0):
        self.name = name
        self.base = service_url(name)
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        rid = current_request_id.get()
        return {HEADER: rid} if rid else {}

    def get(self, path: str, **params):
        try:
            r = httpx.get(f"{self.base}{path}", params={k: v for k, v in params.items() if v is not None},
                          headers=self._headers(), timeout=self.timeout)
        except httpx.TimeoutException:
            raise HTTPException(504, f"{self.name} 응답 시간 초과")
        except httpx.HTTPError as e:
            raise HTTPException(502, f"{self.name} 호출 실패: {e}")
        if r.status_code >= 400:
            raise HTTPException(502, f"{self.name} 오류 응답 {r.status_code}")
        return r.json()

    def post(self, path: str, json: dict):
        try:
            r = httpx.post(f"{self.base}{path}", json=json, headers=self._headers(), timeout=self.timeout)
        except httpx.TimeoutException:
            raise HTTPException(504, f"{self.name} 응답 시간 초과")
        except httpx.HTTPError as e:
            raise HTTPException(502, f"{self.name} 호출 실패: {e}")
        if r.status_code >= 400:
            raise HTTPException(502, f"{self.name} 오류 응답 {r.status_code}")
        return r.json()

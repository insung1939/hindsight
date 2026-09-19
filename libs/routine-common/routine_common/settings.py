import os


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def allowed_origins() -> list[str]:
    return [o.strip() for o in (env("ALLOWED_ORIGINS", "http://localhost:5173") or "").split(",") if o.strip()]


def service_url(name: str) -> str:
    """다른 서비스 주소. 환경변수 <NAME>_URL 이 없으면 로컬 기본 포트를 쓴다."""
    defaults = {
        "market-data": "http://localhost:8001",
        "income": "http://localhost:8002",
        "portfolio": "http://localhost:8003",
        "plan": "http://localhost:8004",
        "backtest": "http://localhost:8005",
    }
    key = name.upper().replace("-", "_") + "_URL"
    url = (env(key, defaults[name]) or "").rstrip("/")
    if url and "://" not in url:  # Render Blueprint 의 fromService host 는 호스트명만 준다
        url = ("http://" if url.startswith(("localhost", "127.")) else "https://") + url
    return url

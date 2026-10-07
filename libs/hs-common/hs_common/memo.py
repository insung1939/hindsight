"""짧은 TTL 메모 — 데이터가 하루 한 번 바뀌는데 요청마다 count(*) 를 네 번 치는 현황 조회 같은 것에 쓴다.
프로세스 안 메모리에만 두고, /internal/sync 가 끝나면 memo_ttl.clear() 로 비운다."""
import functools
import threading
import time

_store: dict = {}
_lock = threading.Lock()


def memo_ttl(seconds: int = 300):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__module__, fn.__qualname__, repr(args[1:]) if args else "", repr(sorted(kwargs.items())))
            now = time.time()
            with _lock:
                hit = _store.get(key)
                if hit and hit[0] > now:
                    return hit[1]
            val = fn(*args, **kwargs)
            with _lock:
                _store[key] = (now + seconds, val)
            return val
        return wrapper
    return deco


def clear() -> None:
    with _lock:
        _store.clear()


memo_ttl.clear = clear

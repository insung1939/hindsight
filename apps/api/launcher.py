"""서비스 4개 + 게이트웨이를 한 프로세스 트리로 띄운다 (Render 웹 서비스 1개 = 컨테이너 1개).
서비스는 각자 폴더에서 uvicorn 으로, 게이트웨이는 $PORT 로. 자식이 죽으면 전체를 내려 Render 가 다시 올리게 한다."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "services").exists() else Path("/app")
SERVICES = {"market-data": 8001, "youtube": 8002, "mentions": 8003, "stats": 8004}
PORT = os.getenv("PORT", "8000")
procs: list[subprocess.Popen] = []


def env_for() -> dict:
    e = dict(os.environ)
    for svc, port in SERVICES.items():  # 서비스 간 호출은 컨테이너 안 포트로
        e[svc.upper().replace("-", "_") + "_URL"] = f"http://127.0.0.1:{port}"
    return e


def start_services():
    for svc, port in SERVICES.items():
        cwd = ROOT / "services" / svc
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port),
                              "--no-access-log"], cwd=cwd, env=env_for())
        procs.append(p)
    deadline = time.time() + 120
    pending = dict(SERVICES)
    while pending and time.time() < deadline:
        for svc, port in list(pending.items()):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=2).status_code == 200:
                    print(f"[launcher] {svc} up on {port}", flush=True)
                    pending.pop(svc)
            except Exception:  # noqa: BLE001
                pass
        time.sleep(1)
    if pending:
        print(f"[launcher] 기동 안 됨: {list(pending)} — 게이트웨이는 올리고 502 로 알린다", flush=True)


def shutdown(*_):
    for p in procs:
        p.terminate()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    start_services()
    gw = subprocess.Popen([sys.executable, "-m", "uvicorn", "gateway:app", "--host", "0.0.0.0", "--port", PORT, "--proxy-headers",
                           "--forwarded-allow-ips", "*"], cwd=Path(__file__).resolve().parent, env=env_for())
    procs.append(gw)
    while True:  # 자식 하나라도 죽으면 전부 내린다
        for p in procs:
            if p.poll() is not None:
                print(f"[launcher] 프로세스 종료 code={p.returncode} → 전체 종료", flush=True)
                shutdown()
        time.sleep(5)

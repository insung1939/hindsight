"""contracts/*.yaml 에서 docs/api.md (발표 필수 문서 1: API 설명) 를 만든다.  python scripts/gen_api_docs.py"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["market-data", "youtube", "mentions", "stats"]
CALLS = {"market-data": "—", "youtube": "—", "mentions": "youtube, market-data", "stats": "mentions, market-data"}


def body_schema(op: dict) -> str:
    content = op.get("requestBody", {}).get("content", {})
    for mt, v in content.items():
        ref = v.get("schema", {}).get("$ref", "")
        return ref.split("/")[-1] if ref else mt
    return "—"


def response_schema(op: dict) -> str:
    for code in ("200", "201", "204"):
        r = op.get("responses", {}).get(code)
        if r is None:
            continue
        content = r.get("content", {})
        for v in content.values():
            ref = v.get("schema", {}).get("$ref", "")
            return f"{code} {ref.split('/')[-1] if ref else 'json'}"
        return f"{code}"
    return "—"


def params(op: dict) -> str:
    out = [p["name"] for p in op.get("parameters", []) if p["name"] != "X-Request-ID"]
    return ", ".join(out) or "—"


lines = ["# API 설명 문서", "",
         "`contracts/*.yaml`(OpenAPI 3.1)에서 자동 생성. 자세한 요청·응답 형식은 각 서비스의 `/docs`(Swagger UI) 또는 명세 파일을 본다.", "",
         "공통 규약: 경로 `/v1/…` kebab-case · 필드 snake_case · 목록은 `items`+`next_cursor` · 오류는 RFC 9457 `application/problem+json` · 요청 헤더 `X-Request-ID` 전파.", ""]
for svc in ORDER:
    spec = yaml.safe_load((ROOT / "contracts" / f"{svc}.yaml").read_text(encoding="utf-8"))
    info = spec["info"]
    lines += [f"## {svc}", "", f"{info.get('description', '')}", "",
              f"- 소유: `{info.get('x-owner')}` · 호출하는 서비스: {CALLS[svc]}",
              f"- 서버: " + ", ".join(f"`{s['url']}`" for s in spec.get("servers", [])), "",
              "| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |", "|---|---|---|---|---|---|"]
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            lines.append(f"| {method.upper()} | `{path}` | {op.get('summary', '')} | {params(op)} | {body_schema(op)} | {response_schema(op)} |")
    lines.append("")
(ROOT / "docs" / "api.md").write_text("\n".join(lines), encoding="utf-8")
print("wrote docs/api.md")

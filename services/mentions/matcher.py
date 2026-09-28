"""종목 매칭 — 이 프로젝트의 심장. 규칙은 PLAN.md 4장.

1. 사전(이름·별칭 → asset_id)을 긴 표현부터 정렬해 정확 문자열 매칭한다("삼성전자우" 가 "삼성전자" 보다 먼저).
2. 매칭된 구간은 지워서 겹쳐 잡히지 않게 한다(삼성전자우 → 삼성전자 중복 방지).
3. 흔한 단어(ambiguous)는 단독 매칭 금지.
4. 영문 티커·별칭은 단어 경계로만 잡는다("V" 가 아무 데나 붙지 않게). 2글자 이하 영문은 무시.
5. 결과: (asset_id, matched_text, confidence). 정식 이름 1.0, 별칭 0.8.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    text: str
    asset_id: str
    confidence: float
    is_ascii: bool


def build_terms(dictionary: list[dict], ambiguous: set[str]) -> list[Term]:
    terms: dict[str, Term] = {}
    for e in dictionary:
        cands = [(e["name"], 1.0)] + [(a, 0.8) for a in e.get("aliases", [])]
        for text, conf in cands:
            t = text.strip()
            if not t or t in ambiguous or e.get("ambiguous") and t == e["name"]:
                continue
            is_ascii = t.isascii()
            if is_ascii and len(t) <= 2:  # "V", "MA", "KT" 같은 짧은 영문은 오탐이 많다
                continue
            key = t.lower()
            if key not in terms or conf > terms[key].confidence:
                terms[key] = Term(t, e["asset_id"], conf, is_ascii)
    # 긴 표현 우선
    return sorted(terms.values(), key=lambda x: (-len(x.text), x.text))


def match(text: str, terms: list[Term]) -> list[tuple[str, str, float]]:
    """text 에서 종목을 찾는다. 반환: [(asset_id, matched_text, confidence)] — 종목당 최고 confidence 하나."""
    if not text:
        return []
    work = text
    found: dict[str, tuple[str, float]] = {}
    for t in terms:
        if t.is_ascii:
            pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(t.text) + r"(?![A-Za-z0-9])", re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(t.text))
        m = pattern.search(work)
        if not m:
            continue
        prev = found.get(t.asset_id)
        if not prev or t.confidence > prev[1]:
            found[t.asset_id] = (m.group(0), t.confidence)
        work = pattern.sub(" " * len(t.text), work)  # 잡힌 구간은 지운다
    return [(aid, txt, conf) for aid, (txt, conf) in found.items()]

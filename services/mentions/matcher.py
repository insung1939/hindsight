"""종목 매칭 — 이 프로젝트의 심장. 규칙은 PLAN.md 4장.

1. 사전(이름·별칭 → asset_id)을 긴 표현부터 정렬해 정확 문자열 매칭한다("삼성전자우" 가 "삼성전자" 보다 먼저).
2. 매칭된 구간은 지워서 겹쳐 잡히지 않게 한다.
3. 흔한 단어(ambiguous)는 단독 매칭 금지. 2글자 이하 영문, 1글자 한글은 무시.
4. 영문은 단어 경계로만. 5자 이하 전부 대문자인 티커(NVDA, BTC)는 대소문자를 구분한다("link" 가 LINK 를 잡지 않게).
5. 자동 수집된 코인(curated=False — "리스크", "온도", "블러" 같은 일반 단어 이름이 많다)은
   채널이 코인 채널이거나 제목에 코인 문맥 단어가 있을 때만 잡는다.
6. 결과: (asset_id, matched_text, confidence). 정식 이름 1.0, 별칭 0.8.
"""
import re
from dataclasses import dataclass

# 테마 표현과 겹치지만 종목·업종을 뜻하지 않는 말 — 매칭 전에 지운다 ("한국은행 금리" 가 은행주로 잡히지 않게)
STOPLIST = ("한국은행", "중앙은행", "투자은행", "연방준비", "게임체인저", "머니게임", "조선일보", "조선시대", "조선왕조", "로봇청소기", "금리", "금융위", "금감원", "금투세")
_STOP_RE = __import__("re").compile("|".join(map(__import__("re").escape, sorted(STOPLIST, key=len, reverse=True))))

_PARTICLES = r"(?:이|가|은|는|을|를|의|도|와|과|로|에|만|주가|주|株|랑|부터|까지|에서|한테)"

CRYPTO_CONTEXT = ("코인", "크립토", "비트", "알트", "업비트", "바이낸스", "빗썸", "이더", "가상자산", "암호화폐", "블록체인", "crypto", "bitcoin", "$")


@dataclass(frozen=True)
class Term:
    text: str
    asset_id: str
    confidence: float
    is_ascii: bool
    market: str
    curated: bool
    pattern: re.Pattern


def build_terms(dictionary: list[dict], ambiguous: set[str]) -> list[Term]:
    terms: dict[str, Term] = {}
    for e in dictionary:
        cands = [(e["name"], 1.0)] + [(a, 0.8) for a in e.get("aliases", [])]
        for text, conf in cands:
            t = text.strip()
            if not t or t in ambiguous or e.get("ambiguous") and t == e["name"]:
                continue
            is_ascii = t.isascii()
            if (is_ascii and len(t) <= 2) or len(t) < 2:
                continue
            if not e.get("curated", True) and not is_ascii and len(t) <= 2 and conf == 1.0:
                continue  # 자동 수집(DART) 2글자 회사명("대상", "동양", "하나" …)은 일상어와 겹쳐 단독 매칭하지 않는다
            if is_ascii:
                flags = 0 if (t.isupper() and len(t) <= 5) else re.IGNORECASE  # 5자 이하 대문자 = 티커
                # 영문 앞뒤에 한글이 바로 붙으면 다른 단어다("SOL글로벌DRAM" 의 SOL 은 솔라나가 아니다). 조사("BTC가", "NVDA를")는 허용.
                pattern = re.compile(r"(?<![A-Za-z0-9가-힣])" + re.escape(t) + r"(?:(?![A-Za-z0-9가-힣])|(?=" + _PARTICLES + r"(?![가-힣])))", flags)
            elif e.get("curated", True):
                pattern = re.compile(re.escape(t))
            else:
                # 자동 수집(DART) 한글 회사명: 앞은 한글이 아니어야 하고, 뒤는 한글이 아니거나 조사·'주가'로 끝나야 한다.
                # "아스트라"→아스트, "이지스탁"→이지스, "스트레스"→트레스, "오로라투자자문"→오로라 같은 부분 일치를 막는다.
                pattern = re.compile(r"(?<![가-힣])" + re.escape(t) + r"(?:(?![가-힣])|(?=" + _PARTICLES + r"(?![가-힣])))")
            key = t if (is_ascii and t.isupper() and len(t) <= 5) else t.lower()
            if key not in terms or conf > terms[key].confidence:
                terms[key] = Term(t, e["asset_id"], conf, is_ascii, e.get("market", ""), bool(e.get("curated", True)), pattern)
    return sorted(terms.values(), key=lambda x: (-len(x.text), x.text))


def has_crypto_context(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in CRYPTO_CONTEXT)


def match(text: str, terms: list[Term], crypto_channel: bool = False) -> list[tuple[str, str, float]]:
    """text 에서 종목을 찾는다. 반환: [(asset_id, matched_text, confidence)] — 종목당 최고 confidence 하나."""
    if not text:
        return []
    work = _STOP_RE.sub(lambda m: " " * len(m.group(0)), text)
    ctx = crypto_channel or has_crypto_context(text)
    found: dict[str, tuple[str, float]] = {}
    for t in terms:
        if t.market == "CRYPTO" and not t.curated and not ctx:
            continue
        m = t.pattern.search(work)
        if not m:
            continue
        prev = found.get(t.asset_id)
        if not prev or t.confidence > prev[1]:
            found[t.asset_id] = (m.group(0), t.confidence)
        work = t.pattern.sub(lambda mm: " " * len(mm.group(0)), work)  # 잡힌 구간은 지운다
    return [(aid, txt, conf) for aid, (txt, conf) in found.items()]

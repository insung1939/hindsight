"""매칭 규칙 테스트 — PLAN.md 4장의 규칙이 그대로 코드로 지켜지는지."""
from matcher import build_terms, match

DICT = [
    {"asset_id": "KRX:005930", "name": "삼성전자", "aliases": ["삼전"], "market": "KRX", "ambiguous": False},
    {"asset_id": "KRX:005935", "name": "삼성전자우", "aliases": [], "market": "KRX", "ambiguous": False},
    {"asset_id": "KRX:000660", "name": "SK하이닉스", "aliases": ["하닉", "하이닉스"], "market": "KRX", "ambiguous": False},
    {"asset_id": "KRX:030200", "name": "KT", "aliases": [], "market": "KRX", "ambiguous": True},
    {"asset_id": "US:NVDA", "name": "NVIDIA", "aliases": ["엔비디아"], "market": "US", "ambiguous": False},
    {"asset_id": "US:V", "name": "Visa", "aliases": ["비자"], "market": "US", "ambiguous": False},
    {"asset_id": "CRYPTO:KRW-BTC", "name": "비트코인", "aliases": ["BTC"], "market": "CRYPTO", "ambiguous": False},
    {"asset_id": "CRYPTO:KRW-RE", "name": "리", "aliases": ["RE"], "market": "CRYPTO", "ambiguous": False},
    {"asset_id": "CRYPTO:KRW-LSK", "name": "리스크", "aliases": ["LSK"], "market": "CRYPTO", "ambiguous": False, "curated": False},
    {"asset_id": "CRYPTO:KRW-LINK", "name": "체인링크", "aliases": ["LINK"], "market": "CRYPTO", "ambiguous": False, "curated": False},
]
TERMS = build_terms(DICT, {"KT", "비자"})


def ids(text):
    return {aid for aid, _, _ in match(text, TERMS)}


def test_exact_and_alias():
    assert ids("삼성전자 지금 사도 될까") == {"KRX:005930"}
    hits = dict((a, c) for a, _, c in match("삼전 하닉 비교", TERMS))
    assert hits == {"KRX:005930": 0.8, "KRX:000660": 0.8}


def test_longer_name_wins_and_no_double_count():
    assert ids("삼성전자우 배당") == {"KRX:005935"}


def test_ambiguous_not_matched_alone():
    assert ids("KT 요금제") == set()
    assert ids("비자 발급") == set()  # 별칭이 모호 목록에 있으면 제외


def test_ascii_word_boundary():
    assert ids("NVIDIA earnings") == {"US:NVDA"}
    assert ids("BTC 10만 달러") == {"CRYPTO:KRW-BTC"}
    assert ids("MYBTCX") == set()  # 단어 경계 없음
    assert ids("nvidia 소식") == {"US:NVDA"}  # 대소문자 무시


def test_no_text():
    assert match("", TERMS) == []


def test_single_char_name_ignored():
    assert ids("리플 전망과 리스크 정리") == set()  # "리" 한 글자는 무시, "리플"은 사전에 없음


def test_uncurated_crypto_needs_context():
    assert ids("하반기 증시 리스크 점검") == set()                       # 일반 단어
    assert ids("코인 시장 리스크 코인 급등") == {"CRYPTO:KRW-LSK"}          # 코인 문맥
    assert {a for a, _, _ in match("리스크 코인 전망", TERMS, crypto_channel=True)} == {"CRYPTO:KRW-LSK"}


def test_uppercase_ticker_case_sensitive():
    assert ids("Subscribe link below") == set()
    assert ids("코인 LINK 급등") == {"CRYPTO:KRW-LINK"}

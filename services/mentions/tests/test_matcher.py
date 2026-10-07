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


# ── 테마(업종) 사전과 스톱리스트 (docs/data-plan.md D2) ──
THEME_DICT = DICT + [
    {"asset_id": "KRX:091160", "name": "반도체", "aliases": ["반도체주"], "market": "KRX", "asset_type": "theme", "ambiguous": False},
    {"asset_id": "KRX:091170", "name": "은행", "aliases": ["은행주", "금융주"], "market": "KRX", "asset_type": "theme", "ambiguous": False},
    {"asset_id": "KRX:042700", "name": "한미반도체", "aliases": [], "market": "KRX", "ambiguous": False},
]
THEME_TERMS = build_terms(THEME_DICT, {"KT", "비자", "은행"})  # 맨 "은행"은 흔한 단어라 모호 목록에, 복합 표현만 잡는다


def tids(text):
    return {aid for aid, _, _ in match(text, THEME_TERMS)}


def test_theme_without_ticker():
    assert tids("반도체 급등, 지금이라도 올라타야 하나") == {"KRX:091160"}


def test_longer_stock_name_beats_theme_and_both_can_coexist():
    assert tids("한미반도체 실적 발표") == {"KRX:042700"}  # "반도체" 는 지워진 구간이라 테마로 다시 잡히지 않는다
    assert tids("삼성전자 덕에 반도체 전체가 들썩") == {"KRX:005930", "KRX:091160"}


def test_stoplist_prevents_false_theme():
    assert tids("한국은행 금리 동결") == set()  # "한국은행" 은 매칭 전에 지운다
    assert tids("은행주 배당 시즌") == {"KRX:091170"}


def test_auto_two_char_corp_name_not_matched():
    terms = build_terms(DICT + [{"asset_id": "KRX:001680", "name": "대상", "aliases": [], "market": "KRX", "ambiguous": False, "curated": False},
                                {"asset_id": "KRX:005930X", "name": "삼전", "aliases": [], "market": "KRX", "ambiguous": False, "curated": True}], set())
    assert {a for a, _, _ in match("투자 대상 종목 정리", terms)} == set()
    assert {a for a, _, _ in match("삼전 간다", terms)} == {"KRX:005930X"}


def test_auto_korean_name_needs_word_boundary():
    auto = [{"asset_id": "KRX:067390", "name": "아스트", "aliases": [], "market": "KRX", "ambiguous": False, "curated": False},
            {"asset_id": "KRX:347700", "name": "스피어", "aliases": [], "market": "KRX", "ambiguous": False, "curated": False},
            {"asset_id": "KRX:090710", "name": "휴림로봇", "aliases": [], "market": "KRX", "ambiguous": False, "curated": False}]
    terms = build_terms(DICT + auto, set())
    got = lambda t: {a for a, _, _ in match(t, terms)}  # noqa: E731
    assert got("GPT 신모델 아스트라 효과") == set()               # 긴 단어 속 부분 일치 금지
    assert got("투자자의 스트레스 푸는 법") == set()
    assert got("[스피어 주가 전망] 지금이 기회") == {"KRX:347700"}  # 공백·조사 경계는 허용
    assert got("스피어가 간다 #스피어") == {"KRX:347700"}
    assert got("휴림로봇, 두산로보틱스 비교") == {"KRX:090710"}
    assert got("삼성전자가 산다") == {"KRX:005930"}                # 시드(curated) 는 기존 규칙 그대로


def test_ascii_ticker_not_inside_korean_word():
    assert ids("SOL글로벌DRAM반도체플러스 ETF 출시") == set()   # ETF 이름 속 SOL 은 솔라나가 아니다
    assert ids("BTC가 10만 달러") == {"CRYPTO:KRW-BTC"}         # 조사는 허용
    assert ids("NVIDIA를 샀다") == {"US:NVDA"}

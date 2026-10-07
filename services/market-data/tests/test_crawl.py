"""네이버 증권 종목 뉴스 응답 파싱 (네트워크 없이)."""
from datetime import date

from collectors import parse_naver_news_dates

PAYLOAD = [{"total": 2, "items": [{"datetime": "202610072052", "title": "a"}, {"datetime": "202610070912", "title": "b"}]},
           {"total": 1, "items": [{"datetime": "202610061701", "title": "c"}]}, {"total": 0, "items": [{"datetime": "bad"}]}]


def test_parse_dates():
    assert parse_naver_news_dates(PAYLOAD) == [date(2026, 10, 7), date(2026, 10, 7), date(2026, 10, 6)]

"""초기 자산 목록. 팀원 각자 보유 자산을 여기에 추가한다. source 가 곧 수집 어댑터다."""

SEED_ASSETS = [
    # 국내 (공공데이터포털 — 키 필요). symbol 은 종목코드, name 으로 조회한다.
    {"asset_id": "KRX:005930", "market": "KRX", "symbol": "005930", "name": "삼성전자", "currency": "KRW", "asset_type": "stock", "source": "datagokr"},
    {"asset_id": "KRX:003690", "market": "KRX", "symbol": "003690", "name": "코리안리", "currency": "KRW", "asset_type": "stock", "source": "datagokr"},
    {"asset_id": "KRX:035420", "market": "KRX", "symbol": "035420", "name": "NAVER", "currency": "KRW", "asset_type": "stock", "source": "datagokr"},
    {"asset_id": "KRX:005945", "market": "KRX", "symbol": "005945", "name": "NH투자증권우", "currency": "KRW", "asset_type": "stock", "source": "datagokr"},
    {"asset_id": "KRX:360750", "market": "KRX", "symbol": "360750", "name": "TIGER 미국S&P500", "currency": "KRW", "asset_type": "etf", "expense_ratio": 0.07, "source": "datagokr"},
    {"asset_id": "KRX:133690", "market": "KRX", "symbol": "133690", "name": "TIGER 미국나스닥100", "currency": "KRW", "asset_type": "etf", "expense_ratio": 0.07, "source": "datagokr"},
    {"asset_id": "KRX:371160", "market": "KRX", "symbol": "371160", "name": "TIGER 차이나항셍테크", "currency": "KRW", "asset_type": "etf", "expense_ratio": 0.09, "source": "datagokr"},
    {"asset_id": "KRX:441640", "market": "KRX", "symbol": "441640", "name": "KODEX 미국배당커버드콜액티브", "currency": "KRW", "asset_type": "etf", "expense_ratio": 0.39, "source": "datagokr"},
    # 미국 (Yahoo Finance — 키 불필요). 지수 ETF 원본과 비교용.
    {"asset_id": "US:SPY", "market": "US", "symbol": "SPY", "name": "SPDR S&P 500 ETF", "currency": "USD", "asset_type": "etf", "expense_ratio": 0.0945, "source": "yahoo"},
    {"asset_id": "US:QQQ", "market": "US", "symbol": "QQQ", "name": "Invesco QQQ (Nasdaq-100)", "currency": "USD", "asset_type": "etf", "expense_ratio": 0.20, "source": "yahoo"},
    # 코인 (업비트 — 키 불필요)
    {"asset_id": "CRYPTO:KRW-BTC", "market": "CRYPTO", "symbol": "KRW-BTC", "name": "비트코인", "currency": "KRW", "asset_type": "crypto", "source": "upbit"},
]

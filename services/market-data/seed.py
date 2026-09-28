"""초기 종목 사전. 키 없이 시작하기 위한 최소 목록이며, DART_KEY 가 있으면 corpCode 로 국내 전 상장사가 추가된다.
종목코드는 DART corpCode 와 대조해 검증할 것(팀 B 담당). aliases 는 유튜브 제목에서 실제로 쓰이는 표현을 팀이 계속 보강한다."""

# ── 지수 (초과수익 기준) ──
INDEXES = [
    {"asset_id": "INDEX:KOSPI", "market": "INDEX", "symbol": "^KS11", "name": "코스피", "aliases": [], "currency": "KRW", "asset_type": "index", "source": "yahoo", "tracked": True},
    {"asset_id": "INDEX:SPX", "market": "INDEX", "symbol": "^GSPC", "name": "S&P500", "aliases": [], "currency": "USD", "asset_type": "index", "source": "yahoo", "tracked": True},
]

# ── 국내 (코드, 이름, 별칭, 거래소) ──
_KR = [
    ("005930", "삼성전자", ["삼전"], "KS"), ("000660", "SK하이닉스", ["하이닉스", "하닉"], "KS"),
    ("373220", "LG에너지솔루션", ["엔솔", "LG엔솔"], "KS"), ("207940", "삼성바이오로직스", ["삼바"], "KS"),
    ("005380", "현대차", ["현대자동차"], "KS"), ("000270", "기아", ["기아차"], "KS"),
    ("068270", "셀트리온", [], "KS"), ("105560", "KB금융", [], "KS"), ("035420", "NAVER", ["네이버"], "KS"),
    ("006400", "삼성SDI", [], "KS"), ("051910", "LG화학", [], "KS"), ("055550", "신한지주", ["신한금융"], "KS"),
    ("005490", "POSCO홀딩스", ["포스코홀딩스", "포스코"], "KS"), ("012330", "현대모비스", ["모비스"], "KS"),
    ("028260", "삼성물산", [], "KS"), ("035720", "카카오", [], "KS"), ("012450", "한화에어로스페이스", ["한화에어로"], "KS"),
    ("032830", "삼성생명", [], "KS"), ("086790", "하나금융지주", ["하나금융"], "KS"), ("096770", "SK이노베이션", ["SK이노"], "KS"),
    ("066570", "LG전자", [], "KS"), ("000810", "삼성화재", [], "KS"), ("033780", "KT&G", [], "KS"),
    ("034020", "두산에너빌리티", ["두산에너"], "KS"), ("259960", "크래프톤", [], "KS"), ("042700", "한미반도체", [], "KS"),
    ("009150", "삼성전기", [], "KS"), ("017670", "SK텔레콤", ["SKT"], "KS"), ("030200", "KT", [], "KS"),
    ("003690", "코리안리", [], "KS"), ("005940", "NH투자증권", [], "KS"), ("039490", "키움증권", ["키움"], "KS"),
    ("006800", "미래에셋증권", ["미래에셋"], "KS"), ("015760", "한국전력", ["한전"], "KS"), ("064350", "현대로템", [], "KS"),
    ("010140", "삼성중공업", [], "KS"), ("009540", "HD한국조선해양", ["한국조선해양"], "KS"), ("042660", "한화오션", [], "KS"),
    ("079550", "LIG넥스원", [], "KS"), ("329180", "HD현대중공업", ["현대중공업"], "KS"), ("323410", "카카오뱅크", ["카뱅"], "KS"),
    ("352820", "하이브", [], "KS"), ("003230", "삼양식품", [], "KS"), ("000100", "유한양행", [], "KS"),
    ("138040", "메리츠금융지주", ["메리츠금융"], "KS"), ("402340", "SK스퀘어", [], "KS"), ("003670", "포스코퓨처엠", [], "KS"),
    ("326030", "SK바이오팜", [], "KS"), ("271560", "오리온", [], "KS"), ("454910", "두산로보틱스", [], "KS"),
    ("247540", "에코프로비엠", [], "KQ"), ("086520", "에코프로", [], "KQ"), ("196170", "알테오젠", [], "KQ"),
    ("028300", "HLB", ["에이치엘비"], "KQ"), ("277810", "레인보우로보틱스", [], "KQ"), ("068760", "셀트리온제약", [], "KQ"),
    ("263750", "펄어비스", [], "KQ"),
]

# ── 미국 (티커, 이름, 별칭) — 한국 유튜브에서 자주 나오는 표현 위주 ──
_US = [
    ("NVDA", "NVIDIA", ["엔비디아", "엔비"]), ("TSLA", "Tesla", ["테슬라"]), ("AAPL", "Apple", ["애플"]),
    ("MSFT", "Microsoft", ["마이크로소프트", "마소"]), ("AMZN", "Amazon", ["아마존"]), ("GOOGL", "Alphabet", ["알파벳", "구글"]),
    ("META", "Meta", ["메타"]), ("NFLX", "Netflix", ["넷플릭스"]), ("AMD", "AMD", []), ("INTC", "Intel", ["인텔"]),
    ("AVGO", "Broadcom", ["브로드컴"]), ("TSM", "TSMC", ["티에스엠씨"]), ("PLTR", "Palantir", ["팔란티어"]),
    ("COIN", "Coinbase", ["코인베이스"]), ("MSTR", "Strategy", ["마이크로스트래티지", "마스트"]), ("BRK-B", "Berkshire Hathaway", ["버크셔"]),
    ("JPM", "JPMorgan", ["JP모건", "제이피모건"]), ("LLY", "Eli Lilly", ["일라이릴리", "릴리"]), ("NVO", "Novo Nordisk", ["노보노디스크"]),
    ("COST", "Costco", ["코스트코"]), ("WMT", "Walmart", ["월마트"]), ("DIS", "Disney", ["디즈니"]), ("BA", "Boeing", ["보잉"]),
    ("SBUX", "Starbucks", ["스타벅스"]), ("NKE", "Nike", ["나이키"]), ("V", "Visa", ["비자"]), ("MA", "Mastercard", ["마스터카드"]),
    ("XOM", "ExxonMobil", ["엑슨모빌"]), ("PFE", "Pfizer", ["화이자"]), ("JNJ", "Johnson & Johnson", ["존슨앤존슨"]),
    ("ARM", "Arm", ["암홀딩스"]), ("QCOM", "Qualcomm", ["퀄컴"]), ("ORCL", "Oracle", ["오라클"]), ("CRM", "Salesforce", ["세일즈포스"]),
    ("ADBE", "Adobe", ["어도비"]), ("UBER", "Uber", ["우버"]), ("RIVN", "Rivian", ["리비안"]), ("SMCI", "Super Micro", ["슈퍼마이크로"]),
    ("IONQ", "IonQ", ["아이온큐"]), ("RKLB", "Rocket Lab", ["로켓랩"]), ("HIMS", "Hims & Hers", ["힘스"]),
    ("SPY", "SPDR S&P 500 ETF", ["S&P500 ETF"]), ("QQQ", "Invesco QQQ", ["나스닥100 ETF"]), ("SOXL", "SOXL", ["속슬"]),
    ("TQQQ", "TQQQ", ["티큐"]), ("SCHD", "SCHD", ["슈드"]), ("JEPI", "JEPI", ["제피"]), ("JEPQ", "JEPQ", ["제픽"]),
]

# ── 코인: 업비트 마켓 목록(키 불필요)으로 sync 때 전부 채운다. 여기엔 시작용 몇 개만. ──
_CRYPTO = [
    ("KRW-BTC", "비트코인", ["BTC", "빗코"]), ("KRW-ETH", "이더리움", ["ETH", "이더"]), ("KRW-XRP", "리플", ["XRP"]),
    ("KRW-SOL", "솔라나", ["SOL"]), ("KRW-DOGE", "도지코인", ["DOGE", "도지"]),
]


def seed_assets() -> list[dict]:
    out = list(INDEXES)
    for code, name, aliases, ex in _KR:
        out.append({"asset_id": f"KRX:{code}", "market": "KRX", "symbol": code, "name": name, "aliases": aliases,
                    "currency": "KRW", "asset_type": "stock", "source": "datagokr", "yahoo_symbol": f"{code}.{ex}",
                    "benchmark_id": "INDEX:KOSPI", "tracked": True, "curated": True})
    for ticker, name, aliases in _US:
        out.append({"asset_id": f"US:{ticker}", "market": "US", "symbol": ticker, "name": name, "aliases": aliases,
                    "currency": "USD", "asset_type": "etf" if ticker in ("SPY", "QQQ", "SOXL", "TQQQ", "SCHD", "JEPI", "JEPQ") else "stock",
                    "source": "yahoo", "benchmark_id": "INDEX:SPX", "tracked": True, "curated": True})
    for mkt, name, aliases in _CRYPTO:
        out.append({"asset_id": f"CRYPTO:{mkt}", "market": "CRYPTO", "symbol": mkt, "name": name, "aliases": aliases,
                    "currency": "KRW", "asset_type": "crypto", "source": "upbit", "benchmark_id": "CRYPTO:KRW-BTC", "tracked": True, "curated": True})
    return out


# 단독으로는 종목을 가리키지 않는 흔한 단어 — mentions 가 매칭에서 제외한다
AMBIGUOUS_NAMES = {"KT", "LG", "SK", "한국", "대한", "동양", "삼성", "현대", "한화", "두산", "메타", "비자", "암홀딩스", "구글"}

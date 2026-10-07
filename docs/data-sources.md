# 데이터 출처

발표 필수 항목(명칭 · 제공 기관 · 출처 URL · 수집 항목). 인증키는 `.env` 로만 다룬다.

| 데이터 | 명칭 · 기관 | URL | 방식 | 수집 항목 | 갱신 | 서비스 |
|---|---|---|---|---|---|---|
| 채널·영상 메타 | YouTube Data API v3 · Google (수업 제공) | https://developers.google.com/youtube/v3 | Open API (키) | 채널 id·구독자 수, 영상 id·제목·설명·게시일·조회수. 채널 51개(선정 기준 [channel-selection.md](channel-selection.md)), 최근 1년 | 일 1회 | youtube |
| 상장사 이름·종목코드 | DART OpenAPI corpCode · 금융감독원 (수업 제공) | https://opendart.fss.or.kr | Open API (키) | corp_name, stock_code | 월 1회 | market-data |
| 국내 일별 시세 | 금융위원회_주식시세정보(V2) · 공공데이터포털 | https://www.data.go.kr/data/15094808/openapi.do (엔드포인트 `GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2`) | Open API (키) | 기준일, 종목명, 종가, 거래량 | 일 1회 | market-data |
| 미국 시세 · 지수 · 국내 대체 시세 · **업종 ETF** | Yahoo Finance chart API | https://finance.yahoo.com | HTTP JSON (키 불필요) | 일자, 종가, 거래량 (`^KS11` 코스피, `^GSPC` S&P500, `005930.KS`, 테마 대표 ETF `091160.KS` 등 20개) | 일 1회 | market-data |
| 코인 마켓 목록 · 일봉 | 업비트 Open API · 두나무 | https://docs.upbit.com | Open API (키 불필요) | 마켓·한글명, 일자(KST)·종가·거래량 | 일 1회 | market-data |
| 종목별 일별 뉴스 기사 수 | **크롤링** 네이버 증권 종목 뉴스 · 네이버 | https://m.stock.naver.com/domestic/stock/005930/news | 웹 페이지가 화면을 그릴 때 부르는 엔드포인트(`/api/news/stock/<코드>`, 20건/쪽)를 읽음. BeautifulSoup 는 HTML 표가 폐기(410)되어 쓰지 않음 | 기사 날짜 → 일별 건수 (하루 300건 상한) | 일 1회, 국내 추적 종목 100개 × 7일 | market-data |
| 공시 목록 | DART 공시검색 `list.json` · 금융감독원 | https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001 | Open API (키) | 접수번호, 접수일, 공시명(→ 실적·계약·자금조달·주요사항·지분·기타 분류). 언급된 국내 종목만 | 일 1회 | market-data |

메모
- YouTube 는 `search.list`(100 유닛)를 쓰지 않고 채널 업로드 재생목록(`playlistItems.list`, 50개당 1 유닛)만 읽는다. 채널 20개 × 1년 백필도 수백 유닛. 하루 한도 10,000.
- 자막·댓글은 수집하지 않는다. 채널 실명은 저장은 하되 API 응답·화면·통계에 내지 않는다.
- 업비트 일봉은 초당 10회 제한이라 429 면 잠깐 쉬고 재시도한다. 업비트 KRW 마켓 전부(약 280개)를 사전에 넣되 언급된 것만 시세를 긁는다.
- 시드 종목코드(국내 57개)는 DART corpCode 로 검증한다. 별칭 사전과 업종·테마 사전(20개, 테마 → 대표 ETF)은 `services/market-data/seed.py` 에서 팀이 계속 보강한다.
- 데이터가 각각 어떤 질문에 답하는지는 [data-plan.md](data-plan.md).

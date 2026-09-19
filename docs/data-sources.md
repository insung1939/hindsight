# 데이터 출처

발표 필수 항목(명칭 · 제공 기관 · 출처 URL · 수집 항목). 인증키는 `.env` 로만 다룬다.

| 데이터 | 명칭 · 기관 | URL | 방식 | 수집 항목 | 갱신 | 서비스 |
|---|---|---|---|---|---|---|
| 국내 주식·ETF 일별 시세 | 금융위원회_주식시세정보 · 공공데이터포털 | https://www.data.go.kr/data/15094808/openapi.do | Open API (키) | 기준일, 종목명, 종가 | 일 1회 | market-data |
| 미국 ETF 일별 시세 | Yahoo Finance chart API · Yahoo | https://finance.yahoo.com | HTTP JSON (키 불필요) | 일자, 종가 | 일 1회 | market-data |
| 비트코인 일봉 | 업비트 Open API · 두나무 | https://docs.upbit.com | Open API (키 불필요) | 일자(KST), 종가 | 일 1회 | market-data |
| 공식 고시환율 | 환율 Open API · 한국수출입은행 | https://www.koreaexim.go.kr/ir/HPHKIR020M01 | Open API (키) | 통화, 매매기준율 | 일 1회 | market-data |
| 환율 이력 (백테스트용) | Yahoo Finance `USDKRW=X`, `HKDKRW=X` | https://finance.yahoo.com | HTTP JSON | 일자, 환율 | 일 1회 | market-data |
| 배당 결정 공시 | DART OpenAPI · 금융감독원 | https://opendart.fss.or.kr | Open API (키) | 배당기준일, 주당배당금 | 일 1회 | income (6주차) |
| 국내 ETF 분배금 | 운용사 상품 페이지 (TIGER · KODEX 등) | 운용사별 | 크롤링 | 분배락일, 지급일, 분배금 | 월 1회 | income (5주차) |

메모
- Stooq 는 2026년 9월 현재 JavaScript 검증을 요구해 스크립트 수집이 안 된다. Yahoo 로 대체.
- 업비트 일봉은 한 번에 200개까지라 `to` 파라미터로 거슬러 올라가며 받는다.
- 공공데이터포털 시세 API 는 종목명(`itmsNm`)으로 조회한다. 하루 호출 한도(개발계정 10,000)에 맞춰 최근 구간만 매일, 과거 구간은 최초 1회 백필.

# 세미나 데모 런북 — "MSA 환경에서 REST API를 효율적으로 관리하는 방법"

힌드사이트 저장소 하나로 Before/After 를 보여준다. 순서: **OpenAPI → Spectral → oasdiff → (Pact) → APISIX → OpenTelemetry/Grafana → Backstage → Kubernetes**.
각 단계는 "문제 → 도구 → 화면에서 보이는 것" 으로 말한다. 준비: `make compose-all` (서비스 4개 + 게이트웨이 + 관측 스택), `make up` 없이도 됨.

## 0. 무대 — 서비스 4개, 호출 관계

- `README.md` 의 호출 그래프. "API 가 5개 서비스 × 4~15개 = 40개 남짓. 팀 5명이면 이미 문서·규칙·호환성·추적·담당자 문제가 생긴다."
- 각 서비스 `/docs` 를 열면 **문서가 5군데로 흩어진 상태** 가 Before.

## 1. 문서 파편화 → OpenAPI 중앙화 (`contracts/`)

- `contracts/*.yaml` 5개가 단일 진실 공급원. `docs/api.md` 는 여기서 자동 생성(`make docs`).
- 구현이 명세와 어긋나면 `tests/test_contract.py` 가 실패한다. 시연: `services/stats/main.py` 에 엔드포인트 하나를 몰래 추가 → `make test` 실패 메시지 "구현에는 있는데 명세에 없음".

## 2. 규칙 불일치 → Spectral

- `contracts/.spectral.yaml`: `/v1` 접두사·kebab-case·snake_case·problem+json·x-owner.
- 시연: 명세에서 `next_cursor` 를 `nextCursor` 로 바꾸고 `make lint` → `hindsight-property-snake-case` 오류. CI(`.github/workflows/contracts.yml`)가 PR 을 막는다.

## 3. Breaking Change → oasdiff

- 시연(로컬): 
  ```bash
  cp contracts/market-data.yaml /tmp/base.yaml
  # contracts/market-data.yaml 에서 PriceOut.currency 를 지운다
  docker run --rm -v /tmp:/base -v $PWD/contracts:/head tufin/oasdiff breaking /base/base.yaml /head/market-data.yaml
  ```
  → `response-property-removed` ERR. PR 에서는 main 대비 자동 비교.
- 포인트: portfolio·plan·backtest 가 이 필드를 쓴다. 명세 단계에서 잡혔으니 배포 후 장애가 아니다.

## 4. 소비자 계약 → Pact (6주차 추가 예정)

- plan → market-data `/v1/assets/{id}/prices/latest` 계약. market-data 가 응답을 바꾸면 plan 의 계약 테스트가 먼저 깨진다.

## 5. 게이트웨이 → APISIX (`platform/gateway/apisix.yaml`)

Before: 프론트 `.env` 에 서비스 주소 5개, 인증·속도제한 없음, `/internal/sync` 가 외부에 노출.
After: 주소 하나 `http://localhost:9080/api/<service>/...`.

```bash
curl -i http://localhost:9080/api/plan/v1/instructions?portfolio_id=1            # 401 — 키 없음
curl -s -H "apikey: hindsight-web-dev-key" http://localhost:9080/api/plan/v1/instructions?portfolio_id=1 | head -c 200
curl -i -X POST -H "apikey: hindsight-web-dev-key" http://localhost:9080/api/market-data/internal/sync   # 403 — 내부 엔드포인트 차단
for i in $(seq 1 35); do curl -s -o /dev/null -w "%{http_code} " -H "apikey: hindsight-demo-key" http://localhost:9080/api/backtest/v1/runs/1; done  # 30번째부터 429
curl -s http://localhost:9091/apisix/prometheus/metrics | grep apisix_http_status | head
```

## 6. 장애 추적 → OpenTelemetry + Tempo + Grafana

- 서비스는 `OTEL_EXPORTER_OTLP_ENDPOINT` 만 있으면 자동 계측(`hs_common/telemetry.py`). 코드 수정 없음.
- 시연: 지시서 생성 한 번 → Grafana(http://localhost:3000) → Explore → Tempo → Search service `plan` → 트레이스 하나가 **plan → portfolio → market-data** 세 서비스를 거치는 것을 본다. `X-Request-ID` 응답 헤더로도 같은 요청을 찾는다.
- 장애 주입: `docker compose -f platform/compose/docker-compose.yml stop market-data` → 프론트에서 지시서 생성 → 502 problem+json `detail: "market-data 호출 실패"` → 트레이스에서 어느 span 이 실패했는지 확인 → `start market-data`.

## 7. 담당자·위치 → Backstage (`platform/backstage/catalog-info.yaml`)

- Component 4 + API 4, owner, `dependsOn`, `consumesApis`. Backstage 에 URL 등록하면 의존성 그래프와 OpenAPI 뷰어가 뜬다.
- 라이브 Backstage 가 무거우면 catalog 파일과 스크린샷으로 대체.

## 8. 배포·확장·복구 → Kubernetes (`platform/k8s/base`)

```bash
kubectl apply -k platform/k8s/base
kubectl -n hindsight get pods
kubectl -n hindsight delete pod -l app=market-data   # 되살아남
kubectl -n hindsight scale deploy/stats --replicas=3
```

## 9. 상용 대안과 규모

- Datadog: 위 6번을 통합 제공, 비용. Istio: 서비스가 수십 개·팀이 여럿일 때 mTLS·서킷브레이커를 인프라로 강제. 지금 규모에선 게이트웨이 + OTel 로 충분하다는 판단을 말한다.

## 한 줄 결론

"API 가 늘어나도 통제되는 이유는 도구가 아니라 **순서**다 — 명세 먼저, 규칙은 CI 가, 호환성은 diff 가, 입구는 하나, 추적은 자동, 담당자는 카탈로그에."

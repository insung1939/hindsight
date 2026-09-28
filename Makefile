# 자주 쓰는 명령 모음.  make help
SERVICES := market-data youtube mentions stats
COMPOSE  := docker compose -f platform/compose/docker-compose.yml

.PHONY: help setup up down smoke test lint contracts docs web compose compose-all compose-down

help:            ## 이 목록
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:           ## 가상환경 + 의존성 (최초 1회)
	python3 -m venv .venv && . .venv/bin/activate && pip install -q -e libs/hs-common pytest pyyaml \
	  $(foreach s,$(SERVICES),-r services/$(s)/requirements.txt)
	cd apps/web && npm install

up:              ## 서비스 4개 로컬 실행 (8001~8004)
	./scripts/dev_up.sh

down:            ## 로컬 서비스 종료
	./scripts/dev_down.sh

smoke:           ## 사전·시세 → 샘플 영상 → 매칭 → 수익률 한 바퀴
	. .venv/bin/activate && python scripts/smoke.py

test:            ## 서비스별 pytest (계약 드리프트 포함)
	@for s in $(SERVICES); do echo "== $$s"; (cd services/$$s && ../../.venv/bin/python -m pytest -q) || exit 1; done

lint:            ## Spectral 로 contracts 검사
	npx -y @stoplight/spectral-cli@6 lint "contracts/*.yaml" --ruleset contracts/.spectral.yaml --fail-severity error

contracts:       ## 구현에서 명세 재생성 (명세 먼저 고치는 게 원칙 — 결과 diff 를 리뷰)
	. .venv/bin/activate && python scripts/export_contracts.py && $(MAKE) lint

docs:            ## docs/api.md 재생성
	. .venv/bin/activate && python scripts/gen_api_docs.py

web:             ## 프론트 개발 서버 (5173)
	cd apps/web && npm run dev

compose:         ## Docker 로 서비스 4개
	$(COMPOSE) up -d --build

compose-all:     ## + APISIX 게이트웨이 + OTel·Tempo·Prometheus·Grafana (세미나)
	$(COMPOSE) --profile gateway --profile observability up -d --build

compose-down:    ## compose 전체 종료
	$(COMPOSE) --profile gateway --profile observability down

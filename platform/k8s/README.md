# platform/k8s — 세미나 실험실 (7주차)

kind(로컬) → EC2 k3s. 같은 GHCR 이미지를 쓴다.
- `base/`      Deployment·Service ×5, ConfigMap(서비스 URL), Secret(DB·키)
- `apisix/`    게이트웨이 standalone — 라우팅 · 키 인증 · rate-limit
- `otel/`      OTel Collector → Tempo(트레이스) · Prometheus(메트릭) · Grafana
- `cron/`      CronJob → /internal/sync (GitHub Actions sync.yml 대체)

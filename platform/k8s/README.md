# platform/k8s — 세미나 실험실 (7주차)

같은 GHCR 이미지를 쿠버네티스에 올린다. 로컬 minikube/kind → EC2 k3s 순서.

```bash
cp base/secret.example.yaml base/secret.yaml      # 값 채우고 kustomization.yaml 에서 주석 해제
kubectl apply -k base
kubectl -n hindsight get pods,svc
kubectl -n hindsight port-forward svc/plan 8004:8000
```

- `base/`     Namespace · ConfigMap(서비스 간 DNS 주소) · Secret · Deployment+Service ×5 · CronJob(수집)
- `gateway/`  (7주차) APISIX — platform/gateway/apisix.yaml 을 ConfigMap 으로 마운트
- `otel/`     (7주차) OTel Collector · Tempo · Prometheus · Grafana — platform/compose 의 설정을 재사용

데모 포인트: `kubectl -n hindsight delete pod -l app=market-data` 로 죽여도 되살아나고, `kubectl -n hindsight scale deploy/backtest --replicas=3` 으로 늘어난다.

# 합본 이미지: 서비스 4개 + 게이트웨이. 빌드 컨텍스트 = 저장소 루트.
#   docker build -f apps/api/Dockerfile -t hindsight/api . && docker run -p 8000:8000 --env-file .env hindsight/api
FROM python:3.12-slim
WORKDIR /app
COPY libs/hs-common /app/libs/hs-common
COPY services/market-data/requirements.txt /tmp/req-market.txt
RUN pip install --no-cache-dir -r /tmp/req-market.txt /app/libs/hs-common
COPY services /app/services
COPY apps/api /app/apps/api
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "/app/apps/api/launcher.py"]

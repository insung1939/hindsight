# 빌드 컨텍스트 = 저장소 루트.  docker build -f services/market-data/Dockerfile -t routine/market-data .
FROM python:3.12-slim
WORKDIR /app
COPY libs/hs-common /libs/hs-common
COPY services/market-data/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt /libs/hs-common
COPY services/market-data/ ./
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

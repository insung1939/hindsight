# 빌드 컨텍스트 = 저장소 루트.  docker build -f services/youtube/Dockerfile -t routine/youtube .
FROM python:3.12-slim
WORKDIR /app
COPY libs/hs-common /libs/hs-common
COPY services/youtube/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt /libs/hs-common
COPY services/youtube/ ./
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

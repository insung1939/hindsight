# 빌드 컨텍스트 = 저장소 루트.  docker build -f services/plan/Dockerfile -t routine/plan .
FROM python:3.12-slim
WORKDIR /app
COPY libs/routine-common /libs/routine-common
COPY services/plan/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt /libs/routine-common
COPY services/plan/ ./
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

# 빌드 컨텍스트 = 저장소 루트.  docker build -f services/income/Dockerfile -t routine/income .
FROM python:3.12-slim
WORKDIR /app
COPY libs/routine-common /libs/routine-common
COPY services/income/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt /libs/routine-common
COPY services/income/ ./
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

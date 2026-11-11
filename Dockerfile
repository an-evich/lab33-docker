# Этап 1: builder - ставим зависимости
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Этап 2: финальный образ - только пакеты и код
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app.py .

ARG APP_VERSION=1.0.0
ENV PATH=/root/.local/bin:$PATH \
    APP_VERSION=$APP_VERSION \
    PORT=5000 \
    REDIS_HOST=redis REDIS_PORT=6379 \
    POSTGRES_HOST=postgres POSTGRES_PORT=5432 \
    POSTGRES_DB=lab33 POSTGRES_USER=lab33 POSTGRES_PASSWORD=lab33pass

EXPOSE 5000
CMD ["python", "app.py"]

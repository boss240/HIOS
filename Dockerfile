FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN addgroup --system hios && adduser --system --ingroup hios hios
WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY app ./app
COPY migrations ./migrations
COPY docs/api ./docs/api
COPY web ./web
RUN chown -R hios:hios /app
USER hios

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["sh", "-c", "python -m app.migrate && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT}"]

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --create-home --uid 10001 tar
COPY backend /app/backend
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
RUN mkdir -p /app/data/artifacts && chown -R tar:tar /app/data
USER tar

EXPOSE 8000
CMD ["uvicorn","backend.app.production:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips=*"]

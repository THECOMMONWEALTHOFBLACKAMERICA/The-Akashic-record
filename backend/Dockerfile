FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend /app/backend
ENV PYTHONPATH=/app
CMD ["uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"]

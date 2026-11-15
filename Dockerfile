FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GENIO_DATA_DIR=/data/genio-os

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY core ./core
COPY web ./web
COPY config.json ./
COPY scripts ./scripts

VOLUME ["/data/genio-os"]
EXPOSE 8099

# الـ host يتحدّد من config.json (افتراضيًا 127.0.0.1) — داخل الحاوية نفتحو
# على 0.0.0.0 بورت مقفول على الـ loopback متاع المضيف في docker-compose.
CMD ["python", "-m", "uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8099"]

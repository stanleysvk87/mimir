FROM python:3.12-slim

WORKDIR /app

# tesseract-ocr: powers attachment OCR (pytesseract). Kept in the base
# image rather than optional -- it's a small, well-behaved apt package,
# not worth gating behind a build flag.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV MIMIR_DB_PATH=/data/mimir.db
VOLUME ["/data"]

# Non-root, UID 1000: matches the typical single-user homelab host account.
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin mimir \
    && mkdir -p /data && chown -R mimir:mimir /data /app
USER mimir
ENV HOME=/home/mimir

EXPOSE 8000

# No curl/wget in this slim image -- python is already here. 127.0.0.1, not
# localhost: uvicorn only binds IPv4 (--host 0.0.0.0).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

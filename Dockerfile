FROM python:3.12-slim-bookworm

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    scrot \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV FINAL_EYE_ASSIST=1 \
    FINAL_EYE_LOW_END=1 \
    ZOCR_PORT=9479 \
    PYTHONPATH=/app:/app/GrokMediaFormat

RUN python3 zocr_security.py seal

EXPOSE 9479
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9479/api/health')"

CMD ["python3", "gui/app.py"]
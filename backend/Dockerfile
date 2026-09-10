FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY backend/requirements.txt requirements.txt

# PostgreSQL driver
RUN pip install --no-cache-dir --default-timeout=1000 \
    "psycopg2-binary>=2.9.9"

# Install application dependencies
RUN pip install --no-cache-dir --default-timeout=1000 \
    -r requirements.txt

# Copy application and bundled demo/policy data
COPY backend/ .
COPY data/ ./data/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

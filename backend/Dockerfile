FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY requirements.txt .

# PostgreSQL driver
RUN pip install --no-cache-dir --default-timeout=1000 \
    "psycopg2-binary>=2.9.9"

# Install CPU-only PyTorch wheel
RUN pip install --no-cache-dir --default-timeout=1000 \
    torch --extra-index-url https://download.pytorch.org/whl/cpu

# Install remaining application dependencies
RUN pip install --no-cache-dir --default-timeout=1000 \
    -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for PDF processing and OCR
# Clean cache first to avoid hash mismatches
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    openssl \
    libpoppler-cpp-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-slv \
    tesseract-ocr-eng \
    libgl1-mesa-dri \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (CPU-only torch to avoid CUDA bloat)
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org" && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories
# Note: Source code is mounted as volume in docker-compose.yml, not copied here
RUN mkdir -p /app/data_pdf /app/data_processed /app/models

# Run ingestion worker
CMD ["python", "main.py"]


FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Note: Source code is mounted as volume in docker-compose.yml, not copied here

# Expose Dash port
EXPOSE 8050

# Run Dash app
CMD ["python", "app.py"]


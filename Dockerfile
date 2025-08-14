FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config.yaml .
COPY companies_with_locations.csv .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Default command
CMD ["python", "-m", "src.main", "--csv", "companies_with_locations.csv", "--config", "config.yaml", "--since_days", "1"]

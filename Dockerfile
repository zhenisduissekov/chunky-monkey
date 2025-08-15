# Dockerfile
#
# Containerizes the chunky-monkey project for reproducible, secure, and portable execution.
# This Dockerfile sets up a Python 3.x environment, installs dependencies, and configures
# the application to run the daily job pipeline.
#
# Usage:
#   docker build -t chunky-monkey .
#   docker run --env-file .env -v $(pwd)/articles:/app/articles chunky-monkey
#
# Environment variables (see .env.sample) must be provided at runtime.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY articles/ articles/
COPY . .

# Create logs directory (if not mounted)
RUN mkdir -p logs

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1

# Default command to run the orchestrator
CMD ["python", "src/main.py"]

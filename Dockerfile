FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (uncomment if you need lxml, etc.)
# RUN apt-get update && apt-get install -y build-essential libxml2-dev libxslt1-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# Set environment variables for Python (optional, but good for containers)
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]

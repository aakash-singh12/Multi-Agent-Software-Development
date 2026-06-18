# Use official Python lightweight runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set workspace directory
WORKDIR /app

# Install system dependencies (needed if agents run subprocesses or tests)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application directories and files
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY workspace/ ./workspace/
COPY README.md .

# Expose port
EXPOSE 8000

# Start command (main.py dynamically reads $PORT and hosts uvicorn)
CMD ["python", "backend/main.py"]

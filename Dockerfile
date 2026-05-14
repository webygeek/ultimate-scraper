FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright (browser installation is optional - can run separately)
RUN pip install playwright
RUN pip install email-validator python-jose[cryptography] passlib[bcrypt]

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data/output data/storage

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "main.py", "server"]

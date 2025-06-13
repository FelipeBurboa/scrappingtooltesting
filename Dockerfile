# Use Python 3.11 official image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Create downloads directory
RUN mkdir -p downloads

# Expose port
EXPOSE 8000

# Use your existing start.sh script
CMD ["./start.sh"]
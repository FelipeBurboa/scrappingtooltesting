# Use official Playwright image that has all dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

# Set working directory
WORKDIR /app

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

# Use simplified start script since browsers are pre-installed
CMD ["python", "scrapper.py", "--api"]
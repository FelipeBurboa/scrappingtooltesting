#!/bin/bash

# EC2 Deployment Script for Cencosud Scraper
# Run this script on your EC2 instance

set -e  # Exit on error

echo "🚀 Starting deployment of Cencosud Scraper..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo "🐙 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Install Git if not installed
if ! command -v git &> /dev/null; then
    echo "📂 Installing Git..."
    sudo apt-get install -y git
fi

# Clone or update repository
REPO_URL="https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git"  # Update this with your actual repo
APP_DIR="/home/ubuntu/cencosud-scraper"

if [ -d "$APP_DIR" ]; then
    echo "📥 Updating existing repository..."
    cd $APP_DIR
    git pull origin main
else
    echo "📥 Cloning repository..."
    git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "❗ Please edit .env file with your actual credentials:"
    echo "   nano .env"
    echo "   Then run: docker-compose up -d"
    exit 1
fi

# Create downloads directory
mkdir -p downloads

# Build and start the application
echo "🏗️  Building Docker image..."
sudo docker-compose build

echo "🚀 Starting application..."
sudo docker-compose up -d

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Your API is now available at:"
echo "   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
echo ""
echo "📊 API Endpoints:"
echo "   GET  /api/cencosud  - Get existing data"
echo "   POST /api/cencosud  - Run scraping and get fresh data"
echo "   GET  /health        - Health check"
echo "   GET  /docs          - API documentation"
echo ""
echo "📋 Useful commands:"
echo "   sudo docker-compose logs -f           # View logs"
echo "   sudo docker-compose restart           # Restart service"
echo "   sudo docker-compose down              # Stop service"
echo "   sudo docker-compose up -d --build     # Rebuild and restart"
#!/bin/bash

# Check if Playwright browsers are installed, install if missing
if [ ! -d "/root/.cache/ms-playwright" ]; then
    echo "Playwright browsers not found, installing..."
    playwright install chromium
    playwright install-deps chromium
else
    echo "Playwright browsers already installed"
fi

echo "Starting application..."
python scrapper.py --api
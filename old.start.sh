#!/bin/bash

echo "Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

echo "Starting application..."
python scrapper.py --api
#!/usr/bin/env python3
"""
Cencosud Data Scraper - Modular Version
==========================================

This is the modular version of the Cencosud data scraping application.
The application has been refactored into clean, maintainable components:

- config/: Configuration and environment settings
- core/: Core functionality (browser, auth, utils)
- routes/: API route handlers (catalogados, stockdetalle, mermasventas)

Usage:
    python scrapper.py                      # Run catalogados scraping (script mode)
    python scrapper.py --stockdetalle       # Run stock detalle scraping (script mode)  
    python scrapper.py --mermasventas       # Run mermas y ventas scraping (script mode)
    python scrapper.py --api                # Run as FastAPI server

API Endpoints:
    GET  /api/cencosud/catalogados          # Get existing catalogados data
    POST /api/cencosud/catalogados          # Scrape and get fresh catalogados data
    GET  /api/cencosud/stocksdetalle        # Get existing stock detalle data
    POST /api/cencosud/stocksdetalle        # Scrape and get fresh stock detalle data
    GET  /api/cencosud/mermasventas         # Get existing mermas y ventas data
    POST /api/cencosud/mermasventas         # Scrape and get fresh mermas y ventas data
"""

import sys
import uvicorn
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Import route modules
from routes.catalogados import router as catalogados_router, run_catalogados_script_mode
from routes.stockdetalle import router as stockdetalle_router, run_stockdetalle_script_mode
from routes.mermasventas import router as mermasventas_router, run_mermasventas_script_mode
from config.settings import SERVER_PORT, SERVER_HOST


# Initialize FastAPI app
app = FastAPI(
    title="Cencosud Data API (Modular)",
    description="API para obtener datos de Catalogados, Stock Detalle y Mermas y Ventas por Artículo de Cencosud mediante scraping - Versión Modular",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(catalogados_router)
app.include_router(stockdetalle_router)
app.include_router(mermasventas_router)


@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "Cencosud Data API (Modular & Optimized)",
        "version": "2.1.0",
        "architecture": "modular",
        "endpoints": {
            "GET /api/cencosud/catalogados": "Obtiene datos de catalogados existentes (sin scraping)",
            "POST /api/cencosud/catalogados": "Ejecuta scraping de catalogados y retorna datos actualizados",
            "GET /api/cencosud/stocksdetalle": "Obtiene datos de stock detalle existentes (sin scraping)",
            "POST /api/cencosud/stocksdetalle": "Ejecuta scraping de stock detalle y retorna datos actualizados",
            "GET /api/cencosud/mermasventas": "Obtiene datos de mermas y ventas existentes (sin scraping)",
            "POST /api/cencosud/mermasventas": "Ejecuta scraping de mermas y ventas y retorna datos actualizados",
            "GET /health": "Estado de salud de la API"
        },
        "modules": {
            "config": "Configuration and environment settings",
            "core": "Core functionality (browser, auth, utils)",
            "routes": "API route handlers"
        }
    }


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "cencosud-data-api-modular",
        "version": "2.1.0"
    }


def start_server():
    """Inicia el servidor FastAPI"""
    print(f"Starting modular server on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False
    )


def main():
    """Main entry point with argument parsing"""
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        print("\n" + "="*60)
        print("CENCOSUD DATA API (MODULAR VERSION)")
        print("="*60)
        print("\nArchitecture:")
        print("  📁 config/     - Configuration and settings")
        print("  📁 core/       - Core functionality (auth, browser, utils)")
        print("  📁 routes/     - API route handlers")
        print("  📄 scrapper.py - Entry point (this file)")
        print("\nAPI Server Information:")
        print(f"  🌐 API URL: http://localhost:{SERVER_PORT}")
        print(f"  📖 Docs:   http://localhost:{SERVER_PORT}/docs")
        print(f"  📋 ReDoc:  http://localhost:{SERVER_PORT}/redoc")
        print("\nAvailable Endpoints:")
        print("  GET  /api/cencosud/catalogados     - Obtener datos de catalogados existentes")
        print("  POST /api/cencosud/catalogados     - Scraping + datos de catalogados actualizados")  
        print("  GET  /api/cencosud/stocksdetalle   - Obtener datos de stock detalle existentes")
        print("  POST /api/cencosud/stocksdetalle   - Scraping + datos de stock detalle actualizados")
        print("  GET  /api/cencosud/mermasventas    - Obtener datos de mermas y ventas existentes")
        print("  POST /api/cencosud/mermasventas    - Scraping + datos de mermas y ventas actualizados")
        print("\n⚡ Optimized for speed and modularity")
        print("🔄 Press Ctrl+C to stop the server")
        print("="*60 + "\n")
        
        start_server()
        
    elif len(sys.argv) > 1 and sys.argv[1] == "--stockdetalle":
        print("\n" + "="*60)
        print("CENCOSUD STOCK DETALLE SCRAPER (MODULAR)")
        print("="*60)
        print("\n🔧 Architecture: Modular components")
        print("📊 Mode: Script execution for Stock Detalle")
        print("⚡ Optimized: Faster execution with reduced waits")
        print("\nFor API mode: python scrapper.py --api")
        print("For catalogados: python scrapper.py")
        print("For mermas y ventas: python scrapper.py --mermasventas")
        print("="*60 + "\n")
        
        run_stockdetalle_script_mode()
        
        print("\n" + "="*60)
        print("STOCK DETALLE SCRAPING COMPLETED")
        print("="*60 + "\n")
        
    elif len(sys.argv) > 1 and sys.argv[1] == "--mermasventas":
        print("\n" + "="*60)
        print("CENCOSUD MERMAS Y VENTAS POR ARTÍCULO SCRAPER (MODULAR)")
        print("="*60)
        print("\n🔧 Architecture: Modular components")
        print("📊 Mode: Script execution for Mermas y Ventas por Artículo")
        print("⚡ Optimized: Faster execution with extended wait times")
        print("🚫 Skip: Cadenas selection (not required for this report)")
        print("\nFor API mode: python scrapper.py --api")
        print("For catalogados: python scrapper.py")
        print("For stock detalle: python scrapper.py --stockdetalle")
        print("="*60 + "\n")
        
        run_mermasventas_script_mode()
        
        print("\n" + "="*60)
        print("MERMAS Y VENTAS POR ARTÍCULO SCRAPING COMPLETED")
        print("="*60 + "\n")
        
    else:
        print("\n" + "="*60)
        print("CENCOSUD CATALOGADOS SCRAPER (MODULAR)")
        print("="*60)
        print("\n🔧 Architecture: Modular components")
        print("📊 Mode: Script execution for Catalogados")
        print("⚡ Optimized: Faster execution with reduced waits")
        print("\nFor Stock Detalle: python scrapper.py --stockdetalle")
        print("For Mermas y Ventas: python scrapper.py --mermasventas")
        print("For API mode: python scrapper.py --api")
        print("="*60 + "\n")
        
        run_catalogados_script_mode()
        
        print("\n" + "="*60)
        print("CATALOGADOS SCRAPING COMPLETED")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
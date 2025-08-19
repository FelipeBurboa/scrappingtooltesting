import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.auth import login
from core.browser import (
    select_all_cadenas, 
    click_run_button, 
    click_share_button, 
    click_export_to_excel, 
    click_final_export_button,
    wait_for_agentql_element_fast
)
from core.utils import find_latest_stockdetalle_file, parse_excel_to_json
from config.settings import DOWNLOADS_DIR

router = APIRouter(prefix="/api/cencosud", tags=["stockdetalle"])


def click_stockdetalle_report(page):
    """
    OPTIMIZED: Faster report detection for Stock Detalle
    """
    print("\nNavegando al reporte de Stock Detalle (optimizado)...")
    
    # OPTIMIZED: Skip networkidle wait, go straight to detection
    page.wait_for_timeout(3000)  # Reduced from 10s to 3s
    
    # Try the most successful strategy first
    STOCKDETALLE_REPORT_QUERY = """
   {
        stockdetalle_link(link containing "Maestra - Stock Detalle" text)
    }
    """
    
    print("Buscando enlace al reporte de Stock Detalle...")
    response = wait_for_agentql_element_fast(page, STOCKDETALLE_REPORT_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'stockdetalle_link') and response.stockdetalle_link:
        print("✓ Enlace de Stock Detalle encontrado")
        print("Haciendo clic en el enlace...")
        response.stockdetalle_link.click()
        
        # OPTIMIZED: Wait for URL change instead of networkidle
        try:
            page.wait_for_timeout(5000)  # Wait for navigation
            print("✓ Reporte de Stock Detalle cargado")
        except:
            print("⚠️ Esperando un poco más...")
            page.wait_for_timeout(5000)
        return
    
    # Fallback: Try alternative query
    print("⚠️ Probando búsqueda alternativa...")
    ALTERNATIVE_QUERY = """
    {
        stock_link(link containing "Stock" text)
    }
    """
    
    response = wait_for_agentql_element_fast(page, ALTERNATIVE_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'stock_link') and response.stock_link:
        print("✓ Enlace de Stock encontrado (alternativo)")
        response.stock_link.click()
        page.wait_for_timeout(5000)
        print("✓ Navegación alternativa exitosa")
        return
    
    raise Exception("No se pudo encontrar el enlace al reporte de Stock Detalle")


def main_stockdetalle(headless=False):
    """
    OPTIMIZED: Main function for Stock Detalle with faster execution
    """
    print("\nIniciando proceso optimizado para Stock Detalle...")
    
    browser = None
    playwright = None
    
    try:
        # All steps with optimized timing
        print("\nPASO 1: Login...")
        page, browser, playwright, context = login(headless=headless)
        
        print("\nPASO 2: Navegando al reporte de Stock Detalle...")
        click_stockdetalle_report(page)
        
        print("\nPASO 3: Seleccionando cadenas...")
        select_all_cadenas(page)
        
        print("\nPASO 4: Ejecutando reporte...")
        click_run_button(page)
        
        print("\nPASO 5: Iniciando exportación...")
        click_share_button(page)
        click_export_to_excel(page)
        
        print("\nPASO 6: Descargando...")
        success, download_path = click_final_export_button(page, headless=headless, report_type="stockdetalle")
        
        if success:
            print(f"\n✓ Proceso de Stock Detalle completado: {download_path}")
            return download_path
        else:
            raise Exception("Descarga falló")
        
    except Exception as e:
        print(f"\nError: {e}")
        raise e
        
    finally:
        print("\nLimpiando recursos...")
        if browser:
            browser.close()
        if playwright:
            playwright.stop()


def run_stockdetalle_script_mode():
    """Ejecuta en modo script para Stock Detalle (sin API)"""
    try:
        print("Iniciando proceso optimizado de Stock Detalle...")
        main_stockdetalle(headless=True)
        print("\nScraping de Stock Detalle completado. Convirtiendo...")
        
        excel_file = find_latest_stockdetalle_file()
        if excel_file:
            output_json = f"{DOWNLOADS_DIR}/stockdetalle_data.json"
            json_data = parse_excel_to_json(excel_file, output_json, report_type='stockdetalle')
            if json_data:
                print(f"✓ Conversión exitosa: {len(json_data)} registros")
        
    except Exception as e:
        print(f"Error en el proceso de Stock Detalle: {e}")
        print("Intentando conversión del archivo existente...")
        excel_file = find_latest_stockdetalle_file()
        if excel_file:
            output_json = f"{DOWNLOADS_DIR}/stockdetalle_data.json"
            parse_excel_to_json(excel_file, output_json, report_type='stockdetalle')


@router.get("/stocksdetalle")
async def get_stocksdetalle_data():
    """
    GET: Retorna los datos de stock detalle existentes sin ejecutar scraping
    """
    try:
        print("GET /api/cencosud/stocksdetalle - Obteniendo datos existentes...")
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            excel_file = await loop.run_in_executor(
                executor,
                find_latest_stockdetalle_file
            )
        
        if not excel_file:
            raise HTTPException(
                status_code=404, 
                detail="No se encontró archivo de stock detalle. Ejecute POST primero para generar datos."
            )
        
        with ThreadPoolExecutor() as executor:
            json_data = await loop.run_in_executor(
                executor,
                lambda: parse_excel_to_json(excel_file, report_type='stockdetalle')
            )
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al procesar el archivo Excel de stock detalle")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Datos de stock detalle obtenidos exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "existing_file",
                "report_type": "stocksdetalle",
                "total_records": len(json_data),
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/stocksdetalle")
async def scrape_and_get_stocksdetalle_data():
    """
    POST: Ejecuta scraping de stock detalle completo y retorna los datos actualizados
    """
    try:
        print("POST /api/cencosud/stocksdetalle - Ejecutando scraping optimizado...")
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            download_path = await loop.run_in_executor(
                executor,
                lambda: main_stockdetalle(headless=True)
            )
        
        if not download_path or not os.path.exists(download_path):
            raise HTTPException(status_code=500, detail="El scraping de stock detalle no pudo descargar el archivo")
        
        output_json_path = f"{DOWNLOADS_DIR}/stockdetalle_data.json"
        json_data = parse_excel_to_json(download_path, output_json_path, report_type='stockdetalle')
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al convertir el archivo Excel de stock detalle a JSON")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Scraping de stock detalle optimizado completado exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "fresh_scraping",
                "report_type": "stocksdetalle",
                "total_records": len(json_data),
                "file_saved": output_json_path,
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en scraping de stock detalle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
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
from core.utils import find_latest_catalogados_file, parse_excel_to_json
from config.settings import DOWNLOADS_DIR

router = APIRouter(prefix="/api/cencosud", tags=["catalogados"])


def click_catalogados_report(page):
    """
    OPTIMIZED: Faster report detection for Catalogados
    """
    print("\nNavegando al reporte de Catalogados (optimizado)...")
    
    # OPTIMIZED: Skip networkidle wait, go straight to detection
    page.wait_for_timeout(3000)  # Reduced from 10s to 3s
    
    # Try the most successful strategy first
    CATALOGADOS_REPORT_QUERY = """
    {
        catalogados_link(link containing "Maestra - Catalogados" text)
    }
    """
    
    print("Buscando enlace al reporte...")
    response = wait_for_agentql_element_fast(page, CATALOGADOS_REPORT_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'catalogados_link') and response.catalogados_link:
        print("✓ Enlace encontrado")
        print("Haciendo clic en el enlace...")
        response.catalogados_link.click()
        
        # OPTIMIZED: Wait for specific URL pattern instead of networkidle
        try:
            page.wait_for_url("**/app/3C07ABD2154D804FEAC41B83E17FFE6F/**", timeout=30000)
            print("✓ Reporte cargado - URL cambió")
        except:
            print("⚠️ URL timeout, esperando un poco más...")
            page.wait_for_timeout(5000)
        return
    
    # Fallback: Direct navigation (faster than searching)
    print("⚠️ Usando navegación directa (más rápido)...")
    current_url = page.url
    base_url = current_url.split('/app')[0]
    catalogados_url = f"{base_url}/app/3C07ABD2154D804FEAC41B83E17FFE6F/3E71BF3D1A44F3EB7D0FB6BE68C14C5E"
    
    print(f"Navegando directamente a: {catalogados_url}")
    page.goto(catalogados_url, wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(3000)
    print("✓ Navegación directa exitosa")


def main_catalogados(headless=False):
    """
    OPTIMIZED: Main function for Catalogados with faster execution
    """
    print("\nIniciando proceso optimizado para Catalogados...")
    
    browser = None
    playwright = None
    
    try:
        # All steps with optimized timing
        print("\nPASO 1: Login...")
        page, browser, playwright, context = login(headless=headless)
        
        print("\nPASO 2: Navegando al reporte de Catalogados...")
        click_catalogados_report(page)
        
        print("\nPASO 3: Seleccionando cadenas...")
        select_all_cadenas(page)
        
        print("\nPASO 4: Ejecutando reporte...")
        click_run_button(page)
        
        print("\nPASO 5: Iniciando exportación...")
        click_share_button(page)
        click_export_to_excel(page)
        
        print("\nPASO 6: Descargando...")
        success, download_path = click_final_export_button(page, headless=headless, report_type="catalogados")
        
        if success:
            print(f"\n✓ Proceso de Catalogados completado: {download_path}")
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


def run_catalogados_script_mode():
    """Ejecuta en modo script (sin API)"""
    try:
        print("Iniciando proceso optimizado completo...")
        main_catalogados(headless=True)
        print("\nScraping de catalogados completado. Convirtiendo...")
        
        excel_file = find_latest_catalogados_file()
        if excel_file:
            output_json = f"{DOWNLOADS_DIR}/catalogados_data.json"
            json_data = parse_excel_to_json(excel_file, output_json)
            if json_data:
                print(f"✓ Conversión exitosa: {len(json_data)} registros")
        
    except Exception as e:
        print(f"Error en el proceso de catalogados: {e}")
        print("Intentando conversión del archivo existente...")
        excel_file = find_latest_catalogados_file()
        if excel_file:
            output_json = f"{DOWNLOADS_DIR}/catalogados_data.json"
            parse_excel_to_json(excel_file, output_json)


@router.get("/catalogados")
async def get_catalogados_data():
    """
    GET: Retorna los datos de catalogados existentes sin ejecutar scraping
    """
    try:
        print("GET /api/cencosud/catalogados - Obteniendo datos existentes...")
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            excel_file = await loop.run_in_executor(
                executor,
                find_latest_catalogados_file
            )
        
        if not excel_file:
            raise HTTPException(
                status_code=404, 
                detail="No se encontró archivo de catalogados. Ejecute POST primero para generar datos."
            )
        
        with ThreadPoolExecutor() as executor:
            json_data = await loop.run_in_executor(
                executor,
                lambda: parse_excel_to_json(excel_file)
            )
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al procesar el archivo Excel de catalogados")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Datos de catalogados obtenidos exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "existing_file",
                "report_type": "catalogados",
                "total_records": len(json_data),
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/catalogados")
async def scrape_and_get_catalogados_data():
    """
    POST: Ejecuta scraping de catalogados completo y retorna los datos actualizados
    """
    try:
        print("POST /api/cencosud/catalogados - Ejecutando scraping optimizado...")
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            download_path = await loop.run_in_executor(
                executor,
                lambda: main_catalogados(headless=True)
            )
        
        if not download_path or not os.path.exists(download_path):
            raise HTTPException(status_code=500, detail="El scraping de catalogados no pudo descargar el archivo")
        
        output_json_path = f"{DOWNLOADS_DIR}/catalogados_data.json"
        json_data = parse_excel_to_json(download_path, output_json_path)
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al convertir el archivo Excel de catalogados a JSON")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Scraping de catalogados optimizado completado exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "fresh_scraping",
                "report_type": "catalogados",
                "total_records": len(json_data),
                "file_saved": output_json_path,
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en scraping de catalogados: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
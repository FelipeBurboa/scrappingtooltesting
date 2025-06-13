import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.auth import login
from core.browser import (
    click_run_button, 
    click_share_button, 
    click_export_to_excel, 
    click_final_export_button,
    wait_for_agentql_element_fast
)
from core.utils import find_latest_mermasventas_file, parse_excel_to_json
from config.settings import DOWNLOADS_DIR

router = APIRouter(prefix="/api/cencosud", tags=["mermasventas"])


def click_mermasventas_report(page):
    """
    OPTIMIZED: Faster report detection for Mermas y Ventas por Artículo
    """
    print("\nNavegando al reporte de Mermas y Ventas por Artículo (optimizado)...")
    
    # OPTIMIZED: Skip networkidle wait, go straight to detection
    page.wait_for_timeout(3000)  # Reduced from 10s to 3s
    
    # Try the most successful strategy first
    MERMASVENTAS_REPORT_QUERY = """
    {
        mermasventas_link(link containing "Mermas y Ventas por Artículo" or "Mermas y Ventas" text)
    }
    """
    
    print("Buscando enlace al reporte...")
    response = wait_for_agentql_element_fast(page, MERMASVENTAS_REPORT_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'mermasventas_link') and response.mermasventas_link:
        print("✓ Enlace encontrado")
        print("Haciendo clic en el enlace...")
        response.mermasventas_link.click()
        
        # OPTIMIZED: Wait for specific URL pattern instead of networkidle
        try:
            page.wait_for_timeout(5000)  # Wait for navigation
            print("✓ Reporte cargado")
        except:
            print("⚠️ Esperando un poco más...")
            page.wait_for_timeout(5000)
        return
    
    # Fallback: Try alternative queries
    print("⚠️ Probando búsqueda alternativa...")
    ALTERNATIVE_QUERIES = [
        """
        {
            mermas_link(link containing "Mermas" text)
        }
        """,
        """
        {
            ventas_link(link containing "Ventas por Artículo" text)
        }
        """
    ]
    
    for query in ALTERNATIVE_QUERIES:
        response = wait_for_agentql_element_fast(page, query, max_retries=2, wait_time=2)
        
        if response:
            # Check which attribute exists
            for attr_name in ['mermas_link', 'ventas_link']:
                if hasattr(response, attr_name):
                    element = getattr(response, attr_name)
                    if element:
                        print(f"✓ Enlace encontrado (alternativo): {attr_name}")
                        element.click()
                        page.wait_for_timeout(5000)
                        print("✓ Navegación alternativa exitosa")
                        return
    
    raise Exception("No se pudo encontrar el enlace al reporte de Mermas y Ventas por Artículo")


def click_run_button_mermasventas(page):
    """
    OPTIMIZED: Custom run button for Mermas y Ventas with extended waiting time
    """
    print("\nEjecutando reporte de Mermas y Ventas (optimizado con espera extendida)...")
    
    page.wait_for_timeout(2000)  # Initial wait
    
    RUN_BUTTON_QUERY = """
    {
        run_button(button to execute or run the report)
    }
    """
    
    response = wait_for_agentql_element_fast(page, RUN_BUTTON_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'run_button') and response.run_button:
        print("✓ Botón Run encontrado")
        response.run_button.click()
        
        # EXTENDED WAIT: Mermas y Ventas requires more time to load
        print("Esperando ejecución del reporte (tiempo extendido para Mermas y Ventas)...")
        page.wait_for_timeout(15000)  # Extended from 8s to 15s for this specific report
        
        # Additional check for completion indicators
        print("Verificando finalización del reporte...")
        page.wait_for_timeout(5000)  # Additional 5s buffer
        
        print("✓ Reporte ejecutado")
        return True
    
    raise Exception("No se pudo encontrar el botón Run")


def main_mermasventas(headless=False):
    """
    OPTIMIZED: Main function for Mermas y Ventas por Artículo with faster execution
    """
    print("\nIniciando proceso optimizado para Mermas y Ventas por Artículo...")
    
    browser = None
    playwright = None
    
    try:
        # All steps with optimized timing
        print("\nPASO 1: Login...")
        page, browser, playwright, context = login(headless=headless)
        
        print("\nPASO 2: Navegando al reporte de Mermas y Ventas por Artículo...")
        click_mermasventas_report(page)
        
        # SKIP PASO 3: No cadenas selection for this report
        print("\nPASO 3: Saltando selección de cadenas (no requerido para este reporte)...")
        
        print("\nPASO 4: Ejecutando reporte...")
        click_run_button_mermasventas(page)  # Using custom function with extended wait
        
        print("\nPASO 5: Iniciando exportación...")
        click_share_button(page)
        click_export_to_excel(page)
        
        print("\nPASO 6: Descargando...")
        success, download_path = click_final_export_button(page, headless=headless, report_type="mermasventas")
        
        if success:
            print(f"\n✓ Proceso de Mermas y Ventas por Artículo completado: {download_path}")
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


def run_mermasventas_script_mode():
    """Ejecuta en modo script para Mermas y Ventas por Artículo (sin API)"""
    try:
        print("Iniciando proceso optimizado de Mermas y Ventas por Artículo...")
        main_mermasventas(headless=True)
        print("\nScraping de Mermas y Ventas completado. Convirtiendo...")
        
        excel_file = find_latest_mermasventas_file()
        if excel_file:
            output_json = f"{DOWNLOADS_DIR}/mermasventas_data.json"
            json_data = parse_excel_to_json(excel_file, output_json, report_type='mermasventas')
            if json_data:
                print(f"✓ Conversión exitosa: {len(json_data)} registros")
        
    except Exception as e:
        print(f"Error en el proceso de Mermas y Ventas: {e}")
        print("Intentando conversión del archivo existente...")
        excel_file = find_latest_mermasventas_file()
        if excel_file:
            output_json = f"{DOWNLOADS_DIR}/mermasventas_data.json"
            parse_excel_to_json(excel_file, output_json, report_type='mermasventas')


@router.get("/mermasventas")
async def get_mermasventas_data():
    """
    GET: Retorna los datos de Mermas y Ventas por Artículo existentes sin ejecutar scraping
    """
    try:
        print("GET /api/cencosud/mermasventas - Obteniendo datos existentes...")
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            excel_file = await loop.run_in_executor(
                executor,
                find_latest_mermasventas_file
            )
        
        if not excel_file:
            raise HTTPException(
                status_code=404, 
                detail="No se encontró archivo de Mermas y Ventas por Artículo. Ejecute POST primero para generar datos."
            )
        
        with ThreadPoolExecutor() as executor:
            json_data = await loop.run_in_executor(
                executor,
                lambda: parse_excel_to_json(excel_file, report_type='mermasventas')
            )
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al procesar el archivo Excel de Mermas y Ventas por Artículo")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Datos de Mermas y Ventas por Artículo obtenidos exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "existing_file",
                "report_type": "mermasventas",
                "total_records": len(json_data),
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/mermasventas")
async def scrape_and_get_mermasventas_data():
    """
    POST: Ejecuta scraping de Mermas y Ventas por Artículo completo y retorna los datos actualizados
    """
    try:
        print("POST /api/cencosud/mermasventas - Ejecutando scraping optimizado...")
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            download_path = await loop.run_in_executor(
                executor,
                lambda: main_mermasventas(headless=True)
            )
        
        if not download_path or not os.path.exists(download_path):
            raise HTTPException(status_code=500, detail="El scraping de Mermas y Ventas por Artículo no pudo descargar el archivo")
        
        output_json_path = f"{DOWNLOADS_DIR}/mermasventas_data.json"
        json_data = parse_excel_to_json(download_path, output_json_path, report_type='mermasventas')
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al convertir el archivo Excel de Mermas y Ventas por Artículo a JSON")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Scraping de Mermas y Ventas por Artículo optimizado completado exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "fresh_scraping",
                "report_type": "mermasventas",
                "total_records": len(json_data),
                "file_saved": output_json_path,
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en scraping de Mermas y Ventas por Artículo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
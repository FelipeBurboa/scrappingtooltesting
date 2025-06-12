import os
import json
import pandas as pd
import agentql
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import time

# FastAPI imports
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import uvicorn
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Carga las variables de entorno desde el archivo .env
load_dotenv()
print("Variables de entorno cargadas correctamente")

# Inicializa FastAPI
app = FastAPI(
    title="Cencosud Data API",
    description="API para obtener datos de Catalogados y Stock Detalle de Cencosud mediante scraping",
    version="1.0.0"
)

# Obtiene las credenciales de las variables de entorno
USER_NAME = os.getenv("USER_NAME")
print(f"Usuario configurado: {USER_NAME}")
PASSWORD = os.getenv("PASSWORD")
print("Contraseña configurada")
# Configura la API key para AgentQL
os.environ["AGENTQL_API_KEY"] = os.getenv("AGENTQL_API_KEY")
print("API Key de AgentQL configurada")


def parse_excel_to_json(excel_file_path, output_json_path=None):
    """
    Convierte el archivo Excel de catalogados a formato JSON
    
    Args:
        excel_file_path (str): Ruta al archivo Excel
        output_json_path (str): Ruta donde guardar el archivo JSON (opcional)
    
    Returns:
        list: Lista de diccionarios con los datos del Excel
    """
    print(f"\nIniciando conversión de Excel a JSON...")
    print(f"Archivo Excel: {excel_file_path}")
    
    try:
        # Define qué columnas deben mantenerse como string para preservar formato
        string_columns = {'Artículo': str}  # Preserva ceros iniciales en Artículo
        
        # Lee el archivo Excel comenzando desde la fila 3 (índice 2) que contiene los headers
        print("Leyendo archivo Excel...")
        df = pd.read_excel(excel_file_path, header=2, dtype=string_columns)
        
        # Muestra información básica del DataFrame
        print(f"Número de filas: {len(df)}")
        print(f"Número de columnas: {len(df.columns)}")
        print(f"Columnas encontradas: {list(df.columns)}")
        
        # Limpia los nombres de las columnas (elimina espacios extra)
        df.columns = df.columns.str.strip()
        
        # NUEVA LÍNEA: Skip first row if it's exactly "Total" 
        if len(df) > 0:
            first_row = df.iloc[0]
            # Check if the first column (usually "Día") contains exactly "Total"
            first_value = str(first_row.iloc[0]).strip().lower() if len(first_row) > 0 else ""
            if first_value == 'total':
                print("🗑️ Skipping first row (Total row detected)")
                df = df.iloc[1:].reset_index(drop=True)
                print(f"Filas después de skip: {len(df)}")
        
        # Convierte el DataFrame a una lista de diccionarios
        print("Convirtiendo datos a formato JSON...")
        json_data = []
        
        for index, row in df.iterrows():
            # Crea un diccionario para cada fila
            row_dict = {
                "n": index + 1,  # Número de fila empezando desde 1
            }
            
            # Agrega cada columna al diccionario
            for column in df.columns:
                # Maneja valores NaN/None
                value = row[column]
                if pd.isna(value) or value == 'nan':
                    value = None
                elif column == 'Artículo':
                    # Para la columna Artículo, asegura que se mantenga como string
                    value = str(value).strip() if value is not None else None
                elif isinstance(value, (int, float)) and pd.notna(value):
                    # Mantiene los números como están para otras columnas
                    value = value
                else:
                    # Convierte a string y limpia espacios para el resto
                    value = str(value).strip() if value is not None else None
                
                row_dict[column] = value
            
            json_data.append(row_dict)
        
        print(f"Conversión completada. Total de registros: {len(json_data)}")
        
        # Guarda el archivo JSON si se especifica una ruta
        if output_json_path:
            print(f"\nGuardando archivo JSON en: {output_json_path}")
            with open(output_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=2, default=str)
            print("Archivo JSON guardado exitosamente")
        
        return json_data
        
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo {excel_file_path}")
        return None
    except Exception as e:
        print(f"Error al procesar el archivo Excel: {e}")
        return None


def find_latest_catalogados_file():
    """
    Busca el archivo de catalogados más reciente en la carpeta downloads
    
    Returns:
        str: Ruta al archivo encontrado o None si no se encuentra
    """
    downloads_dir = "./downloads"
    
    if not os.path.exists(downloads_dir):
        print(f"Error: La carpeta {downloads_dir} no existe")
        return None
    
    # Busca archivos que contengan "catalogados" en el nombre
    catalogados_files = []
    for filename in os.listdir(downloads_dir):
        if "catalogados" in filename.lower() and filename.endswith('.xlsx'):
            file_path = os.path.join(downloads_dir, filename)
            catalogados_files.append((file_path, os.path.getmtime(file_path)))
    
    if not catalogados_files:
        print("No se encontraron archivos de catalogados en la carpeta downloads")
        return None
    
    # Retorna el archivo más reciente
    latest_file = max(catalogados_files, key=lambda x: x[1])[0]
    print(f"Archivo de catalogados encontrado: {latest_file}")
    return latest_file


def find_latest_stockdetalle_file():
    """
    Busca el archivo de stock detalle más reciente en la carpeta downloads
    
    Returns:
        str: Ruta al archivo encontrado o None si no se encuentra
    """
    downloads_dir = "./downloads"
    
    if not os.path.exists(downloads_dir):
        print(f"Error: La carpeta {downloads_dir} no existe")
        return None
    
    # Busca archivos que contengan "stockdetalle" o "stock_detalle" en el nombre
    stockdetalle_files = []
    for filename in os.listdir(downloads_dir):
        if ("stockdetalle" in filename.lower() or "stock_detalle" in filename.lower()) and filename.endswith('.xlsx'):
            file_path = os.path.join(downloads_dir, filename)
            stockdetalle_files.append((file_path, os.path.getmtime(file_path)))
    
    if not stockdetalle_files:
        print("No se encontraron archivos de stock detalle en la carpeta downloads")
        return None
    
    # Retorna el archivo más reciente
    latest_file = max(stockdetalle_files, key=lambda x: x[1])[0]
    print(f"Archivo de stock detalle encontrado: {latest_file}")
    return latest_file


def wait_for_agentql_element_fast(page, query, max_retries=3, wait_time=2):
    """
    OPTIMIZED: Faster AgentQL element detection with reduced waits
    """
    for attempt in range(max_retries):
        print(f"AgentQL attempt {attempt + 1}/{max_retries}...")
        
        try:
            # OPTIMIZED: Reduced wait time
            page.wait_for_timeout(wait_time * 1000)
            page.wait_for_page_ready_state()
            
            # OPTIMIZED: Try without networkidle first (faster)
            response = page.query_elements(query)
            
            if response:
                print(f"✓ AgentQL found structure on attempt {attempt + 1}")
                return response
            else:
                print(f"✗ AgentQL returned None on attempt {attempt + 1}")
                # OPTIMIZED: Only wait for networkidle if element not found
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)  # Reduced from 20s to 10s
                except:
                    print("⚠️ NetworkIdle timeout, continuando...")
                
                # Try again after networkidle
                response = page.query_elements(query)
                if response:
                    print(f"✓ AgentQL found structure on attempt {attempt + 1} (after networkidle)")
                    return response
                
        except Exception as e:
            print(f"✗ AgentQL error on attempt {attempt + 1}: {e}")
        
        if attempt < max_retries - 1:
            print(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return None


def enhanced_browser_setup_fast(headless=False):
    """
    OPTIMIZED: Faster browser setup with performance flags
    """
    playwright = sync_playwright().start()
    
    browser = playwright.chromium.launch(
        headless=headless,
          args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-gpu',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-blink-features=AutomationControlled',
            '--no-first-run',
            '--no-default-browser-check',
            '--single-process',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',
            '--disable-javascript-harmony-shipping',
            '--disable-ipc-flooding-protection'
        ]
    )
    
    context = browser.new_context(
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        accept_downloads=True,
        java_script_enabled=True,
        has_touch=False,
        is_mobile=False,
        # OPTIMIZED: Disable unnecessary features
        ignore_https_errors=True
    )
    
    return playwright, browser, context


def login(headless=False):
    """
    OPTIMIZED: Faster login with reduced waits
    """
    print("\nIniciando proceso de login (optimizado para velocidad)...")
    
    INITIAL_URL = "https://datasharing.cencosud.com/MicroStrategyLibraryDS/auth/ui/loginPage"
    print(f"Navegando a: {INITIAL_URL}")

    # Enhanced browser setup
    print("Configurando navegador optimizado...")
    playwright, browser, context = enhanced_browser_setup_fast(headless)
    page = agentql.wrap(context.new_page())

    # OPTIMIZED: Faster navigation
    print("Navegando a la página de login...")
    page.goto(INITIAL_URL, wait_until='domcontentloaded', timeout=30000)  # Reduced timeout
    
    # OPTIMIZED: Reduced stability wait
    print("Esperando estabilidad de la página...")
    page.wait_for_timeout(5000)  # Reduced from 10s to 5s
    page.wait_for_page_ready_state()

    # OPTIMIZED: Skip lazy loading triggers - go straight to form detection
    EMAIL_INPUT_QUERY = """
    {
        login_form {
            username_input
            password_input
            log_in_with_credentials
        }
    }
    """
    
    print("Localizando formulario con AgentQL optimizado...")
    response = wait_for_agentql_element_fast(page, EMAIL_INPUT_QUERY, max_retries=3, wait_time=2)
    
    if not response or not hasattr(response, 'login_form') or not response.login_form:
        raise Exception("AgentQL no pudo encontrar el formulario")
    
    # Validate elements
    login_form = response.login_form
    if not all([login_form.username_input, login_form.password_input, login_form.log_in_with_credentials]):
        raise Exception("Elementos del formulario no encontrados")
    
    print("✓ Elementos validados correctamente")
    
    # OPTIMIZED: Faster form filling
    print("Completando credenciales...")
    login_form.username_input.fill(USER_NAME)
    page.wait_for_timeout(1000)  # Reduced from 2s to 1s
    login_form.password_input.fill(PASSWORD)
    page.wait_for_timeout(1000)  # Reduced from 2s to 1s
    
    print("Haciendo clic en el botón de login...")
    login_form.log_in_with_credentials.click()

    # OPTIMIZED: Faster navigation wait with early exit
    print("Esperando navegación...")
    try:
        page.wait_for_url("**/app?state=ok", timeout=30000)  # Wait for specific URL
        print("✓ Login exitoso - URL cambió directamente")
    except:
        print("⚠️ URL timeout, verificando manualmente...")
        page.wait_for_timeout(3000)
        current_url = page.url
        if "app?state=ok" in current_url:
            print("✓ Login exitoso - URL verificada")
        else:
            raise Exception(f"Login falló - URL actual: {current_url}")
    
    return page, browser, playwright, context


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
        stockdetalle_link(link containing "Maestra - Stock Detalle" or "Stock Detalle" text)
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


def select_all_cadenas(page):
    """
    OPTIMIZED: Faster cadenas selection
    """
    print("\nSeleccionando cadenas (optimizado)...")
    
    # OPTIMIZED: Skip networkidle, go straight to detection
    page.wait_for_timeout(3000)  # Reduced from 10s to 3s
    
    # Try the most successful strategy first
    ADD_ALL_QUERY = """
    {
        add_all_button(button or element with title "Add All")
    }
    """
    
    response = wait_for_agentql_element_fast(page, ADD_ALL_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'add_all_button') and response.add_all_button:
        print("✓ Botón Add All encontrado")
        response.add_all_button.click()
        page.wait_for_timeout(2000)  # Reduced from 5s to 2s
        print("✓ Cadenas seleccionadas")
        return True
    
    # Quick CSS fallback
    try:
        add_all = page.locator('span[title="Add All"]').first
        if add_all.count() > 0:
            print("✓ Add All encontrado con CSS")
            add_all.click()
            page.wait_for_timeout(2000)
            print("✓ Cadenas seleccionadas con CSS")
            return True
    except:
        pass
    
    print("⚠️ Continuando sin selección específica...")
    return True


def click_run_button(page):
    """
    OPTIMIZED: Faster run button detection
    """
    print("\nEjecutando reporte (optimizado)...")
    
    page.wait_for_timeout(2000)  # Reduced from 5s to 2s
    
    RUN_BUTTON_QUERY = """
    {
        run_button(button to execute or run the report)
    }
    """
    
    response = wait_for_agentql_element_fast(page, RUN_BUTTON_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'run_button') and response.run_button:
        print("✓ Botón Run encontrado")
        response.run_button.click()
        
        # OPTIMIZED: Wait for report completion indicators instead of fixed time
        print("Esperando ejecución del reporte...")
        page.wait_for_timeout(8000)  # Reduced from 15s to 8s
        print("✓ Reporte ejecutado")
        return True
    
    raise Exception("No se pudo encontrar el botón Run")


def click_share_button(page):
    """
    OPTIMIZED: Faster share button detection
    """
    print("\nAbriendo menú de compartir (optimizado)...")
    
    page.wait_for_timeout(2000)  # Reduced from 5s to 2s
    
    SHARE_BUTTON_QUERY = """
    {
        share_button(button or element with aria-label "Share")
    }
    """
    
    response = wait_for_agentql_element_fast(page, SHARE_BUTTON_QUERY, max_retries=2, wait_time=2)
    
    if response and hasattr(response, 'share_button') and response.share_button:
        print("✓ Botón Share encontrado")
        response.share_button.click()
        page.wait_for_timeout(1000)  # Reduced from 3s to 1s
        print("✓ Menú abierto")
        return True
    
    # Quick CSS fallback
    try:
        share_btn = page.locator('.icon-tb_share_a').first
        if share_btn.count() > 0:
            print("✓ Share encontrado con CSS")
            share_btn.click()
            page.wait_for_timeout(1000)
            print("✓ Menú abierto con CSS")
            return True
    except:
        pass
    
    raise Exception("No se pudo encontrar el botón Share")


def click_export_to_excel(page):
    """
    OPTIMIZED: Faster Excel export detection
    """
    print("\nIniciando exportación a Excel (optimizado)...")
    
    page.wait_for_timeout(1000)  # Reduced from 3s to 1s
    
    EXPORT_EXCEL_QUERY = """
    {
        export_excel_button(clickable element with text "Export to Excel")
    }
    """
    
    response = wait_for_agentql_element_fast(page, EXPORT_EXCEL_QUERY, max_retries=2, wait_time=1)
    
    if response and hasattr(response, 'export_excel_button') and response.export_excel_button:
        print("✓ Export to Excel encontrado")
        response.export_excel_button.click()
        page.wait_for_timeout(2000)  # Reduced from 5s to 2s
        print("✓ Configuraciones cargadas")
        return True
    
    # Quick CSS fallback
    try:
        excel_btn = page.locator('.mstrd-ExportExcelItemContainer').first
        if excel_btn.count() > 0:
            print("✓ Export to Excel encontrado con CSS")
            excel_btn.click()
            page.wait_for_timeout(2000)
            print("✓ Configuraciones cargadas con CSS")
            return True
    except:
        pass
    
    raise Exception("No se pudo encontrar Export to Excel")


def click_final_export_button(page, headless=False, report_type="catalogados"):
    """
    OPTIMIZED: Faster final export with report type specific naming
    """
    print(f"\nIniciando descarga de {report_type} (optimizado)...")
    
    page.wait_for_timeout(1000)  # Reduced from 3s to 1s
    
    FINAL_EXPORT_QUERY = """
    {
        export_button(button with text "Export" in export settings)
    }
    """
    
    response = wait_for_agentql_element_fast(page, FINAL_EXPORT_QUERY, max_retries=2, wait_time=1)
    
    found_element = None
    if response and hasattr(response, 'export_button') and response.export_button:
        found_element = response.export_button
        print("✓ Botón final Export encontrado")
    else:
        # Quick CSS fallback
        try:
            export_btn = page.locator('.mstrd-Button--primary:has-text("Export")').first
            if export_btn.count() > 0:
                found_element = export_btn
                print("✓ Export encontrado con CSS")
        except:
            pass
    
    if not found_element:
        raise Exception("No se pudo encontrar el botón final Export")
    
    # Handle download
    try:
        print("Configurando descarga...")
        with page.expect_download(timeout=60000) as download_info:  # Reduced timeout
            found_element.click()
        
        download = download_info.value
        
        if headless:
            downloads_dir = "./downloads"
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
            save_path = os.path.join(downloads_dir, f"{report_type}_report_{download.suggested_filename}")
        else:
            save_path = f"{report_type}_report_{download.suggested_filename}"
        
        download.save_as(save_path)
        print(f"✓ Archivo guardado: {save_path}")
        
        return True, save_path
        
    except Exception as e:
        raise Exception(f"Error en la descarga: {e}")


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


def main(headless=False):
    """
    OPTIMIZED: Main function with faster execution (backwards compatibility)
    """
    return main_catalogados(headless)


def test_excel_parsing():
    """
    Función de prueba para convertir el Excel existente a JSON
    """
    print("\n=== CONVERSIÓN EXCEL TO JSON ===")
    
    excel_file = find_latest_catalogados_file()
    
    if excel_file:
        output_json = "./downloads/catalogados_data.json"
        json_data = parse_excel_to_json(excel_file, output_json)
        
        if json_data:
            print(f"✓ Conversión exitosa: {len(json_data)} registros")
            return json_data
        else:
            print("✗ Error en la conversión")
            return None
    else:
        print("✗ No se encontró archivo Excel")
        return None


def test_stockdetalle_parsing():
    """
    Función de prueba para convertir el Excel de Stock Detalle a JSON
    """
    print("\n=== CONVERSIÓN STOCK DETALLE EXCEL TO JSON ===")
    
    excel_file = find_latest_stockdetalle_file()
    
    if excel_file:
        output_json = "./downloads/stockdetalle_data.json"
        json_data = parse_excel_to_json(excel_file, output_json)
        
        if json_data:
            print(f"✓ Conversión exitosa: {len(json_data)} registros")
            return json_data
        else:
            print("✗ Error en la conversión")
            return None
    else:
        print("✗ No se encontró archivo Excel de Stock Detalle")
        return None


# ========================
# API ENDPOINTS
# ========================

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "Cencosud Data API (Optimized)",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/cencosud/catalogados": "Obtiene datos de catalogados existentes (sin scraping)",
            "POST /api/cencosud/catalogados": "Ejecuta scraping de catalogados y retorna datos actualizados",
            "GET /api/cencosud/stocksdetalle": "Obtiene datos de stock detalle existentes (sin scraping)",
            "POST /api/cencosud/stocksdetalle": "Ejecuta scraping de stock detalle y retorna datos actualizados",
            "GET /health": "Estado de salud de la API"
        }
    }


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "cencosud-data-api-optimized"
    }


@app.get("/api/cencosud/catalogados")
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


@app.post("/api/cencosud/catalogados")
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
        
        output_json_path = "./downloads/catalogados_data.json"
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


@app.get("/api/cencosud/stocksdetalle")
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
                lambda: parse_excel_to_json(excel_file)
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


@app.post("/api/cencosud/stocksdetalle")
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
        
        output_json_path = "./downloads/stockdetalle_data.json"
        json_data = parse_excel_to_json(download_path, output_json_path)
        
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


# ========================
# SERVER STARTUP
# ========================

def start_server():
    """Inicia el servidor FastAPI"""
    port = 8000  # Fixed port for Railway
    print(f"Starting optimized server on port: {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False
    )


def run_script_mode():
    """Ejecuta en modo script (sin API)"""
    try:
        print("Iniciando proceso optimizado completo...")
        main_catalogados(headless=True)
        print("\nScraping de catalogados completado. Convirtiendo...")
        test_excel_parsing()
        
    except Exception as e:
        print(f"Error en el proceso de catalogados: {e}")
        print("Intentando conversión del archivo existente...")
        test_excel_parsing()


def run_stockdetalle_script_mode():
    """Ejecuta en modo script para Stock Detalle (sin API)"""
    try:
        print("Iniciando proceso optimizado de Stock Detalle...")
        main_stockdetalle(headless=True)
        print("\nScraping de Stock Detalle completado. Convirtiendo...")
        test_stockdetalle_parsing()
        
    except Exception as e:
        print(f"Error en el proceso de Stock Detalle: {e}")
        print("Intentando conversión del archivo existente...")
        test_stockdetalle_parsing()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        print("\n=== CENCOSUD DATA API (OPTIMIZED) ===\n")
        print("API disponible en: http://localhost:8000")
        print("Documentación: http://localhost:8000/docs")
        print("Endpoints:")
        print("  GET  /api/cencosud/catalogados     - Obtener datos de catalogados existentes")
        print("  POST /api/cencosud/catalogados     - Scraping optimizado + datos de catalogados actualizados")  
        print("  GET  /api/cencosud/stocksdetalle   - Obtener datos de stock detalle existentes")
        print("  POST /api/cencosud/stocksdetalle   - Scraping optimizado + datos de stock detalle actualizados")
        print("\nPresiona Ctrl+C para detener el servidor\n")
        
        start_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "--stockdetalle":
        print("\n=== PROCESO OPTIMIZADO STOCK DETALLE ===\n")
        print("Ejecutando en modo script optimizado para Stock Detalle...")
        print("Para ejecutar como API, use: python scrapper.py --api\n")
        
        run_stockdetalle_script_mode()
        
        print("\n=== FIN DEL PROCESO OPTIMIZADO STOCK DETALLE ===\n")
    else:
        print("\n=== PROCESO OPTIMIZADO CATALOGADOS ===\n")
        print("Ejecutando en modo script optimizado para Catalogados...")
        print("Para ejecutar Stock Detalle, use: python scrapper.py --stockdetalle")
        print("Para ejecutar como API, use: python scrapper.py --api\n")
        
        run_script_mode()
        
        print("\n=== FIN DEL PROCESO OPTIMIZADO CATALOGADOS ===\n")
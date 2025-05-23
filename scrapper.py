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
    title="Cencosud Catalogados API",
    description="API para obtener datos de catalogados de Cencosud mediante scraping",
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
        
        # Muestra una muestra de los primeros registros
        if json_data:
            print("\nMuestra de los primeros 2 registros:")
            for i, record in enumerate(json_data[:2]):
                print(f"Registro {i + 1}: {record}")
        
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


def wait_for_agentql_element(page, query, max_retries=5, wait_time=3):
    """
    Enhanced waiting function specifically for AgentQL in containers
    """
    for attempt in range(max_retries):
        print(f"AgentQL attempt {attempt + 1}/{max_retries}...")
        
        try:
            # Extra wait for DOM to stabilize
            page.wait_for_timeout(wait_time * 1000)
            page.wait_for_page_ready_state()
            
            # Wait for network to be idle (with error handling)
            try:
                page.wait_for_load_state('networkidle', timeout=20000)  # Reduced timeout
            except:
                print("⚠️ NetworkIdle timeout, continuando...")
                page.wait_for_timeout(2000)
            
            # Query with AgentQL
            response = page.query_elements(query)
            
            if response:
                print(f"✓ AgentQL found structure on attempt {attempt + 1}")
                return response
            else:
                print(f"✗ AgentQL returned None on attempt {attempt + 1}")
                
        except Exception as e:
            print(f"✗ AgentQL error on attempt {attempt + 1}: {e}")
        
        if attempt < max_retries - 1:
            print(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            # Try to trigger a re-render
            try:
                page.evaluate("window.dispatchEvent(new Event('resize'))")
            except:
                pass
    
    return None


def enhanced_browser_setup(headless=False):
    """
    Enhanced browser setup specifically for AgentQL in containers
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
            '--single-process'
        ]
    )
    
    context = browser.new_context(
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},  # Larger viewport
        accept_downloads=True,
        java_script_enabled=True,
        # Ensure images load
        has_touch=False,
        is_mobile=False
    )
    
    return playwright, browser, context


def login(headless=False):
    """
    Enhanced login function with AgentQL container fixes
    """
    print("\nIniciando proceso de login (optimizado para containers)...")
    
    INITIAL_URL = "https://datasharing.cencosud.com/MicroStrategyLibraryDS/auth/ui/loginPage"
    print(f"Navegando a: {INITIAL_URL}")

    # Enhanced browser setup
    print("Configurando navegador optimizado para AgentQL...")
    playwright, browser, context = enhanced_browser_setup(headless)
    page = agentql.wrap(context.new_page())

    # Navigate with extra stability
    print("Navegando a la página de login...")
    page.goto(INITIAL_URL, wait_until='domcontentloaded', timeout=60000)
    
    # Multiple stability checks
    print("Esperando estabilidad completa de la página...")
    page.wait_for_load_state('networkidle', timeout=30000)
    page.wait_for_timeout(10000)  # Extra wait
    
    # Trigger any lazy loading
    print("Activando carga de contenido...")
    try:
        page.evaluate("""
            // Scroll to trigger any lazy loading
            window.scrollTo(0, document.body.scrollHeight);
            window.scrollTo(0, 0);
            
            // Trigger resize to ensure proper rendering
            window.dispatchEvent(new Event('resize'));
            
            // Force reflow
            document.body.offsetHeight;
        """)
    except Exception as e:
        print(f"Error en JavaScript: {e}")
    
    page.wait_for_timeout(5000)  # Wait for any triggered loads

    # Enhanced AgentQL query
    EMAIL_INPUT_QUERY = """
    {
        login_form {
            username_input
            password_input
            log_in_with_credentials
        }
    }
    """
    
    print("Intentando localizar formulario con AgentQL mejorado...")
    response = wait_for_agentql_element(page, EMAIL_INPUT_QUERY, max_retries=5, wait_time=5)
    
    if not response or not hasattr(response, 'login_form') or not response.login_form:
        raise Exception("AgentQL no pudo encontrar el formulario después de múltiples intentos")
    
    # Validate all elements before proceeding
    login_form = response.login_form
    
    if not login_form.username_input:
        raise Exception("Campo username_input es None en AgentQL")
    if not login_form.password_input:
        raise Exception("Campo password_input es None en AgentQL")
    if not login_form.log_in_with_credentials:
        raise Exception("Botón log_in_with_credentials es None en AgentQL")
    
    print("✓ Todos los elementos AgentQL validados correctamente")
    
    # Fill form with extra stability
    print("Completando credenciales con AgentQL...")
    
    # Scroll to elements and ensure visibility
    try:
        login_form.username_input.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        login_form.username_input.fill(USER_NAME)
        page.wait_for_timeout(2000)
        
        login_form.password_input.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        login_form.password_input.fill(PASSWORD)
        page.wait_for_timeout(2000)
        
        print("Haciendo clic en el botón de login...")
        login_form.log_in_with_credentials.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        login_form.log_in_with_credentials.click()
    except Exception as e:
        raise Exception(f"Error al interactuar con elementos del formulario: {e}")

    # Wait for navigation
    print("Esperando navegación después del login...")
    try:
        page.wait_for_load_state('networkidle', timeout=60000)  # Increased to 60 seconds
        page.wait_for_timeout(5000)  # Reduced from 10s to 5s
    except Exception as nav_error:
        print(f"⚠️ Timeout en navegación, pero continuando: {nav_error}")
        # Continue anyway, login might still be successful
        page.wait_for_timeout(5000)

    # Verify login success
    current_url = page.url
    print(f"URL después del login: {current_url}")
    
    if "loginPage" in current_url:
        raise Exception("Login falló - aún en página de login")
    
    print("✓ Login exitoso con AgentQL")
    return page, browser, playwright, context


def click_catalogados_report(page):
    """
    Enhanced function to click Catalogados report with AgentQL
    """
    print("\nNavegando al reporte de Catalogados (AgentQL optimizado)...")
    
    # Wait for page stability
    try:
        page.wait_for_load_state('networkidle', timeout=30000)
    except:
        print("⚠️ NetworkIdle timeout, continuando...")
    
    page.wait_for_timeout(10000)
    
    # Trigger any lazy loading
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight); window.scrollTo(0, 0);")
        page.wait_for_timeout(3000)
    except:
        pass
    
    # Multiple query strategies for the Catalogados report
    queries = [
        # Strategy 1: Look for the specific link structure
        """
        {
            catalogados_link(link containing "Maestra - Catalogados" text)
        }
        """,
        # Strategy 2: Look for dossier item with Catalogados
        """
        {
            dossier_item(clickable element with class "mstrd-DossierItem-link" containing "Catalogados")
        }
        """,
        # Strategy 3: Simpler approach
        """
        {
            maestra_catalogados_link(clickable element for "Maestra - Catalogados")
        }
        """,
        # Strategy 4: Look for any element with Catalogados text
        """
        {
            catalogados_element(element containing "Catalogados" that is clickable)
        }
        """
    ]
    
    response = None
    found_element = None
    
    for i, query in enumerate(queries, 1):
        print(f"Probando estrategia {i} para encontrar reporte...")
        response = wait_for_agentql_element(page, query, max_retries=2, wait_time=3)
        
        if response:
            # Try to get the element from different possible attribute names
            possible_attrs = ['catalogados_link', 'dossier_item', 'maestra_catalogados_link', 'catalogados_element']
            
            for attr in possible_attrs:
                if hasattr(response, attr):
                    element = getattr(response, attr)
                    if element:
                        found_element = element
                        print(f"✓ Reporte encontrado con estrategia {i} (atributo: {attr})")
                        break
            
            if found_element:
                break
    
    if not found_element:
        # Final fallback: try direct navigation to the URL you provided
        print("⚠️ No se pudo encontrar el enlace, intentando navegación directa...")
        try:
            # Extract the base URL and try to construct the full URL
            current_url = page.url
            base_url = current_url.split('/app')[0]
            catalogados_url = f"{base_url}/app/3C07ABD2154D804FEAC41B83E17FFE6F/3E71BF3D1A44F3EB7D0FB6BE68C14C5E"
            
            print(f"Navegando directamente a: {catalogados_url}")
            page.goto(catalogados_url, wait_until='domcontentloaded', timeout=60000)
            
            try:
                page.wait_for_load_state('networkidle', timeout=30000)
            except:
                print("⚠️ NetworkIdle timeout en navegación directa, continuando...")
            
            page.wait_for_timeout(5000)
            print("✓ Navegación directa al reporte exitosa")
            return
            
        except Exception as direct_nav_error:
            print(f"✗ Error en navegación directa: {direct_nav_error}")
            raise Exception("No se pudo acceder al reporte de Catalogados con ningún método")
    
    print("✓ Enlace del reporte encontrado con AgentQL")
    print("Haciendo clic en el enlace del reporte...")
    try:
        found_element.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        found_element.click()
    except Exception as e:
        raise Exception(f"Error al hacer clic en el enlace del reporte: {e}")
    
    # Wait for navigation
    try:
        page.wait_for_load_state('networkidle', timeout=60000)  # Increased timeout
        page.wait_for_timeout(5000)
    except Exception as nav_error:
        print(f"⚠️ Timeout en navegación del reporte, continuando: {nav_error}")
        page.wait_for_timeout(5000)
    
    print("✓ Reporte cargado exitosamente")


def select_all_cadenas(page):
    """
    Enhanced cadenas selection with AgentQL
    """
    print("\nSeleccionando cadenas (AgentQL optimizado)...")
    
    # Wait for page stability
    page.wait_for_load_state('networkidle', timeout=30000)
    page.wait_for_timeout(10000)
    
    CADENAS_QUERY = """
    {
        elementos_cadena[]
        boton_add_all
    }
    """
    
    response = wait_for_agentql_element(page, CADENAS_QUERY, max_retries=3, wait_time=5)
    
    if response and hasattr(response, 'boton_add_all') and response.boton_add_all:
        print("✓ Botón Agregar Todo encontrado con AgentQL")
        try:
            response.boton_add_all.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            response.boton_add_all.click()
            
            page.wait_for_timeout(5000)
            page.wait_for_load_state('networkidle', timeout=30000)
            print("✓ Cadenas seleccionadas exitosamente")
            return True
        except Exception as e:
            print(f"Error al seleccionar cadenas: {e}")
            print("⚠️ Continuando sin selección específica de cadenas...")
            return True
    else:
        print("⚠️ No se pudo encontrar botón Agregar Todo, continuando...")
        return True  # Continue anyway


def click_run_button(page):
    """
    Enhanced run button click with AgentQL
    """
    print("\nEjecutando reporte (AgentQL optimizado)...")
    
    page.wait_for_load_state('networkidle', timeout=30000)
    page.wait_for_timeout(5000)
    
    RUN_BUTTON_QUERY = """
    {
        run_button
    }
    """
    
    response = wait_for_agentql_element(page, RUN_BUTTON_QUERY, max_retries=3, wait_time=5)
    
    if not response or not hasattr(response, 'run_button') or not response.run_button:
        raise Exception("AgentQL no pudo encontrar el botón Ejecutar")
    
    print("✓ Botón Ejecutar encontrado con AgentQL")
    try:
        response.run_button.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        response.run_button.click()
        
        page.wait_for_timeout(15000)
        page.wait_for_load_state('networkidle', timeout=30000)
        print("✓ Reporte ejecutado exitosamente")
        return True
    except Exception as e:
        raise Exception(f"Error al ejecutar el reporte: {e}")


def click_share_button(page):
    """
    Enhanced share button click with AgentQL
    """
    print("\nAbriendo menú de compartir (AgentQL optimizado)...")
    
    page.wait_for_load_state('networkidle', timeout=30000)
    page.wait_for_timeout(5000)
    
    SHARE_BUTTON_QUERY = """
    {
        share_button
    }
    """
    
    response = wait_for_agentql_element(page, SHARE_BUTTON_QUERY, max_retries=3, wait_time=5)
    
    if not response or not hasattr(response, 'share_button') or not response.share_button:
        raise Exception("AgentQL no pudo encontrar el botón Compartir")
    
    print("✓ Botón Compartir encontrado con AgentQL")
    try:
        response.share_button.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        response.share_button.click()
        
        page.wait_for_timeout(3000)
        print("✓ Menú de compartir abierto exitosamente")
        return True
    except Exception as e:
        raise Exception(f"Error al abrir menú de compartir: {e}")


def click_export_to_excel(page):
    """
    Enhanced Excel export with AgentQL
    """
    print("\nIniciando exportación a Excel (AgentQL optimizado)...")
    
    page.wait_for_timeout(3000)
    
    EXPORT_EXCEL_QUERY = """
    {
        export_to_excel_button
    }
    """
    
    response = wait_for_agentql_element(page, EXPORT_EXCEL_QUERY, max_retries=3, wait_time=5)
    
    if not response or not hasattr(response, 'export_to_excel_button') or not response.export_to_excel_button:
        raise Exception("AgentQL no pudo encontrar el botón Exportar a Excel")
    
    print("✓ Botón Exportar a Excel encontrado con AgentQL")
    try:
        response.export_to_excel_button.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        response.export_to_excel_button.click()
        
        page.wait_for_timeout(5000)
        print("✓ Configuraciones de exportación cargadas exitosamente")
        return True
    except Exception as e:
        raise Exception(f"Error al exportar a Excel: {e}")


def click_final_export_button(page, headless=False):
    """
    Enhanced final export with AgentQL
    """
    print("\nIniciando descarga del reporte (AgentQL optimizado)...")
    
    page.wait_for_timeout(3000)
    
    FINAL_EXPORT_QUERY = """
    {
        export_button(This button only has Export as a text, and is inside the Export Settings)
    }
    """
    
    response = wait_for_agentql_element(page, FINAL_EXPORT_QUERY, max_retries=3, wait_time=5)
    
    if not response or not hasattr(response, 'export_button') or not response.export_button:
        raise Exception("AgentQL no pudo encontrar el botón final de Exportar")
    
    print("✓ Botón final de Exportar encontrado con AgentQL")
    
    try:
        # Configura el listener del evento de descarga
        print("Configurando listener de descarga...")
        with page.expect_download(timeout=120000) as download_info:  # 2 minutos timeout
            response.export_button.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            response.export_button.click()
        
        # Obtiene la información de la descarga
        print("Obteniendo información de la descarga...")
        download = download_info.value
        
        # Crea el directorio de descargas si no existe (para modo headless)
        if headless:
            print("Creando directorio de descargas...")
            downloads_dir = "./downloads"
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
            save_path = os.path.join(downloads_dir, f"catalogados_report_{download.suggested_filename}")
        else:
            save_path = f"catalogados_report_{download.suggested_filename}"
        
        # Espera a que se complete la descarga y la guarda
        print("Guardando archivo descargado...")
        download.save_as(save_path)
        print(f"Archivo descargado: {download.suggested_filename}")
        print(f"Guardado en: {save_path}")
        
        return True, save_path
        
    except Exception as e:
        raise Exception(f"Error en la descarga final: {e}")


def main(headless=False):
    """
    Función principal que orquesta el inicio de sesión y las acciones posteriores
    """
    print("\nIniciando proceso de automatización (AgentQL optimizado)...")
    
    # Inicializa variables para el manejo de recursos
    browser = None
    playwright = None
    
    try:
        # Paso 1: Inicia sesión y obtiene la página autenticada
        print("\nPASO 1: Iniciando sesión...")
        page, browser, playwright, context = login(headless=headless)
        
        # Paso 2: Navega al reporte de Catalogados
        print("\nPASO 2: Navegando al reporte...")
        click_catalogados_report(page)
        
        # Paso 3: Selecciona todas las cadenas disponibles
        print("\nPASO 3: Seleccionando cadenas...")
        select_all_cadenas(page)
        
        # Paso 4: Ejecuta el reporte con los parámetros seleccionados
        print("\nPASO 4: Ejecutando reporte...")
        click_run_button(page)
        
        # Paso 5: Inicia el proceso de exportación
        print("\nPASO 5: Iniciando exportación...")
        click_share_button(page)
        click_export_to_excel(page)
        
        # Paso 6: Completa la exportación y maneja la descarga
        print("\nPASO 6: Completando exportación...")
        success, download_path = click_final_export_button(page, headless=headless)
        
        if success:
            print(f"\nReporte descargado exitosamente en: {download_path}")
            return download_path
        else:
            print("\nLa descarga falló")
            return None
        
        # Mantiene el navegador abierto un momento para ver los resultados (solo si no está en modo headless)
        if not headless:
            print("\nManteniendo navegador abierto para visualización...")
            page.wait_for_timeout(5000)
        
    except Exception as e:
        print(f"\nOcurrió un error: {e}")
        raise e
        
    finally:
        # Limpia los recursos del navegador y Playwright
        print("\nLimpiando recursos...")
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        print("Proceso finalizado\n")


def test_excel_parsing():
    """
    Función de prueba para convertir el Excel existente a JSON
    """
    print("\n=== PRUEBA DE CONVERSIÓN EXCEL TO JSON ===\n")
    
    # Busca el archivo de catalogados más reciente
    excel_file = find_latest_catalogados_file()
    
    if excel_file:
        # Define la ruta de salida para el JSON
        output_json = "./downloads/catalogados_data.json"
        
        # Convierte el Excel a JSON
        json_data = parse_excel_to_json(excel_file, output_json)
        
        if json_data:
            print(f"\nConversión exitosa. Se generaron {len(json_data)} registros.")
            print(f"Archivo JSON guardado en: {output_json}")
            return json_data
        else:
            print("\nError en la conversión")
            return None
    else:
        print("No se pudo encontrar el archivo Excel para procesar")
        return None
    
    print("\n=== FIN DE LA PRUEBA ===\n")


# ========================
# API ENDPOINTS
# ========================

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "Cencosud Catalogados API (AgentQL Optimized)",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/cencosud": "Obtiene datos existentes (sin scraping)",
            "POST /api/cencosud": "Ejecuta scraping y retorna datos actualizados",
            "GET /health": "Estado de salud de la API"
        }
    }


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "cencosud-catalogados-api-agentql-optimized"
    }


@app.get("/api/cencosud")
async def get_catalogados_data():
    """
    GET: Retorna los datos existentes sin ejecutar scraping
    """
    try:
        print("GET /api/cencosud - Obteniendo datos existentes...")
        
        # Ejecuta la búsqueda y conversión en un hilo separado por consistencia
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
        
        # Convierte Excel a JSON también en un hilo separado
        with ThreadPoolExecutor() as executor:
            json_data = await loop.run_in_executor(
                executor,
                lambda: parse_excel_to_json(excel_file)
            )
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al procesar el archivo Excel")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Datos obtenidos exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "existing_file",
                "total_records": len(json_data),
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.post("/api/cencosud")
async def scrape_and_get_catalogados_data():
    """
    POST: Ejecuta scraping completo y retorna los datos actualizados
    """
    try:
        print("POST /api/cencosud - Ejecutando scraping completo (AgentQL optimizado)...")
        
        # Ejecuta el proceso de scraping en un hilo separado para evitar conflictos asyncio
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            download_path = await loop.run_in_executor(
                executor,
                lambda: main(headless=True)
            )
        
        if not download_path or not os.path.exists(download_path):
            raise HTTPException(status_code=500, detail="El scraping no pudo descargar el archivo")
        
        # Convierte el archivo descargado a JSON
        output_json_path = "./downloads/catalogados_data.json"
        json_data = parse_excel_to_json(download_path, output_json_path)
        
        if not json_data:
            raise HTTPException(status_code=500, detail="Error al convertir el archivo Excel a JSON")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Scraping y conversión completados exitosamente",
                "timestamp": datetime.now().isoformat(),
                "source": "fresh_scraping",
                "total_records": len(json_data),
                "file_saved": output_json_path,
                "data": json_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ========================
# SERVER STARTUP
# ========================

def start_server():
    """Inicia el servidor FastAPI"""
    port = 8000  # Fixed port for Railway
    print(f"Starting server on port: {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False
    )


def run_script_mode():
    """Ejecuta en modo script (sin API)"""
    try:
        print("Iniciando proceso completo: Scraping + Conversión...")
        
        # Ejecuta el scraping (headless para producción)
        main(headless=True)
        
        print("\nScraping completado. Iniciando conversión a JSON...")
        
        # Después del scraping, convierte automáticamente el Excel descargado
        test_excel_parsing()
        
    except Exception as e:
        print(f"Error en el proceso completo: {e}")
        print("Intentando solo la conversión del archivo existente...")
        test_excel_parsing()


# Llama a la función principal
if __name__ == "__main__":
    import sys
    
    # Detecta si se quiere ejecutar como API o como script
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        print("\n=== INICIANDO CENCOSUD CATALOGADOS API (AgentQL Optimized) ===\n")
        print("API disponible en: http://localhost:8000")
        print("Documentación: http://localhost:8000/docs")
        print("Endpoints:")
        print("  GET  /api/cencosud  - Obtener datos existentes")
        print("  POST /api/cencosud  - Scraping + datos actualizados")
        print("\nPresiona Ctrl+C para detener el servidor\n")
        
        start_server()
    else:
        print("\n=== INICIO DEL PROCESO DE AUTOMATIZACIÓN (AgentQL Optimized) ===\n")
        print("Ejecutando en modo script...")
        print("Para ejecutar como API, use: python scrapper.py --api\n")
        
        run_script_mode()
        
        print("\n=== FIN DEL PROCESO DE AUTOMATIZACIÓN ===\n")
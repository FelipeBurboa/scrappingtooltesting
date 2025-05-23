import os
import json
import pandas as pd
import agentql
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

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


def login(headless=False):
    """
    Realiza el inicio de sesión en MicroStrategy Library y guarda el estado de autenticación
    Retorna la página autenticada para interacciones posteriores
    """
    print("\nIniciando proceso de login...")
    
    # URL inicial de la página de inicio de sesión
    INITIAL_URL = "https://datasharing.cencosud.com/MicroStrategyLibraryDS/auth/ui/loginPage"
    print(f"Navegando a: {INITIAL_URL}")

    # Query para localizar los elementos del formulario de inicio de sesión
    EMAIL_INPUT_QUERY = """
    {
        login_form{
        username_input
        password_input
        log_in_with_credentials
        }
    }
    """

    # Inicializa Playwright y configura el navegador
    print("Inicializando Playwright...")
    playwright = sync_playwright().start()
    print("Iniciando navegador...")
    browser = playwright.chromium.launch(headless=headless)
    print("Configurando contexto del navegador...")
    context = browser.new_context(accept_downloads=True)
    print("Creando nueva página...")
    page = agentql.wrap(context.new_page())

    # Navega a la página de inicio de sesión
    print("Navegando a la página de login...")
    page.goto(INITIAL_URL)

    # Localiza y completa el formulario de inicio de sesión
    print("Localizando formulario de login...")
    response = page.query_elements(EMAIL_INPUT_QUERY)
    print("Completando credenciales...")
    response.login_form.username_input.fill(USER_NAME)
    page.wait_for_timeout(1000)  # Espera para asegurar que el campo de usuario se complete
    response.login_form.password_input.fill(PASSWORD)
    page.wait_for_timeout(1000)  # Espera para asegurar que el campo de contraseña se complete
    print("Haciendo clic en el botón de login...")
    response.login_form.log_in_with_credentials.click()

    # Espera a que la página termine de cargar después del inicio de sesión
    print("Esperando a que la página cargue...")
    page.wait_for_page_ready_state()

    # Espera adicional para asegurar que la sesión esté completamente establecida
    print("Esperando a que la sesión se establezca completamente...")
    page.wait_for_timeout(5000)
    
    print("Login completado exitosamente\n")
    return page, browser, playwright, context


def click_catalogados_report(page):
    """
    Hace clic en el reporte Maestra - Catalogados
    """
    print("\nNavegando al reporte de Catalogados...")
    
    # Query para localizar el enlace al reporte de Catalogados
    CATALOGADOS_REPORT_QUERY = """
    {
        maestra_catalogados_link(clickable link for "Maestra - Catalogados" report)
    }
    """
    
    # Localiza y hace clic en el enlace del reporte
    print("Buscando enlace al reporte...")
    response = page.query_elements(CATALOGADOS_REPORT_QUERY)
    print("Haciendo clic en el enlace del reporte...")
    response.maestra_catalogados_link.click()
    # Espera a que la página del reporte termine de cargar
    print("Esperando a que el reporte cargue...")
    page.wait_for_page_ready_state()
    print("Reporte cargado exitosamente\n")


def select_all_cadenas(page):
    """
    Hace clic en el botón Agregar Todo para seleccionar todas las cadenas (JUMBO, SANTA ISABEL, SPID)
    """
    print("\nSeleccionando cadenas...")
    
    # Query para localizar los elementos de cadena y el botón de agregar todo
    CADENAS_QUERY = """
    {
        elementos_cadena[]
        boton_add_all
    }
    """
    
    # Localiza los elementos de la interfaz
    print("Buscando elementos de cadena...")
    response = page.query_elements(CADENAS_QUERY)
    
    if response and hasattr(response, 'boton_add_all') and response.boton_add_all:
        print("Haciendo clic en el botón Agregar Todo...")
        response.boton_add_all.click()
        print("Esperando a que se procese la selección...")
        page.wait_for_timeout(2000)  # Espera para que se procese la selección
        page.wait_for_page_ready_state()
        print("Cadenas seleccionadas exitosamente\n")
        return True
    else:
        print("No se pudo encontrar el botón Agregar Todo\n")
        return False


def click_run_button(page):
    """
    Hace clic en el botón Ejecutar para procesar el reporte con los parámetros seleccionados
    """
    print("\nIniciando ejecución del reporte...")
    
    # Query para localizar el botón de ejecutar
    RUN_BUTTON_QUERY = """
    {
        run_button
    }
    """
    
    # Localiza y hace clic en el botón de ejecutar
    print("Buscando botón de ejecutar...")
    response = page.query_elements(RUN_BUTTON_QUERY)
    
    if response and hasattr(response, 'run_button') and response.run_button:
        print("Haciendo clic en el botón Ejecutar...")
        response.run_button.click()
        print("Esperando a que el reporte comience a procesarse...")
        page.wait_for_timeout(3000)  # Espera para que el reporte comience a procesarse
        page.wait_for_page_ready_state()
        print("Reporte iniciado exitosamente\n")
        return True
    else:
        print("No se pudo encontrar el botón Ejecutar\n")
        return False


def click_share_button(page):
    """
    Hace clic en el botón Compartir para abrir el menú de compartir
    """
    print("\nAbriendo menú de compartir...")
    
    # Query para localizar el botón de compartir
    SHARE_BUTTON_QUERY = """
    {
        share_button
    }
    """
    
    # Localiza y hace clic en el botón de compartir
    print("Buscando botón de compartir...")
    response = page.query_elements(SHARE_BUTTON_QUERY)
    
    if response and hasattr(response, 'share_button') and response.share_button:
        print("Haciendo clic en el botón Compartir...")
        response.share_button.click()
        print("Esperando a que se abra el menú de compartir...")
        page.wait_for_timeout(2000)  # Espera para que se abra el menú de compartir
        print("Menú de compartir abierto exitosamente\n")
        return True
    else:
        print("No se pudo encontrar el botón Compartir\n")
        return False


def click_export_to_excel(page):
    """
    Hace clic en el botón Exportar a Excel desde el menú de compartir
    """
    print("\nIniciando exportación a Excel...")
    
    # Query para localizar el botón de exportar a Excel
    EXPORT_EXCEL_QUERY = """
    {
        export_to_excel_button
    }
    """
    
    # Localiza y hace clic en el botón de exportar a Excel
    print("Buscando botón de exportar a Excel...")
    response = page.query_elements(EXPORT_EXCEL_QUERY)
    
    if response and hasattr(response, 'export_to_excel_button') and response.export_to_excel_button:
        print("Haciendo clic en el botón Exportar a Excel...")
        response.export_to_excel_button.click()
        print("Esperando a que se carguen las configuraciones de exportación...")
        page.wait_for_timeout(2000)  # Espera para que se carguen las configuraciones de exportación
        print("Configuraciones de exportación cargadas exitosamente\n")
        return True
    else:
        print("No se pudo encontrar el botón Exportar a Excel\n")
        return False


def click_final_export_button(page, headless=False):
    """
    Hace clic en el botón final de Exportar en la Configuración de Exportación para iniciar la descarga
    """
    print("\nIniciando descarga del reporte...")
    
    # Query para localizar el botón final de exportar
    FINAL_EXPORT_QUERY = """
    {
        export_button(This button only has Export as a text, and is inside the Export Settings)
    }
    """
    
    # Localiza el botón final de exportar
    print("Buscando botón final de exportar...")
    response = page.query_elements(FINAL_EXPORT_QUERY)
    
    if response and hasattr(response, 'export_button') and response.export_button:
        print("Haciendo clic en el botón final de Exportar...")
        
        # Configura el listener del evento de descarga
        print("Configurando listener de descarga...")
        with page.expect_download() as download_info:
            response.export_button.click()
        
        # Obtiene la información de la descarga
        print("Obteniendo información de la descarga...")
        download = download_info.value
        
        # Crea el directorio de descargas si no existe (para modo headless)
        import os
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
        print(f"Guardado en: {save_path}\n")
        
        return True, save_path
    else:
        print("No se pudo encontrar el botón final de Exportar\n")
        return False, None


def main(headless=False):
    """
    Función principal que orquesta el inicio de sesión y las acciones posteriores
    """
    print("\nIniciando proceso de automatización...")
    
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
        "message": "Cencosud Catalogados API",
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
        "service": "cencosud-catalogados-api"
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
        print("POST /api/cencosud - Ejecutando scraping completo...")
        
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
    port = int(os.getenv("PORT", 8000))  # Railway sets PORT automatically
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
        print("\n=== INICIANDO CENCOSUD CATALOGADOS API ===\n")
        print("API disponible en: http://localhost:8000")
        print("Documentación: http://localhost:8000/docs")
        print("Endpoints:")
        print("  GET  /api/cencosud  - Obtener datos existentes")
        print("  POST /api/cencosud  - Scraping + datos actualizados")
        print("\nPresiona Ctrl+C para detener el servidor\n")
        
        start_server()
    else:
        print("\n=== INICIO DEL PROCESO DE AUTOMATIZACIÓN ===\n")
        print("Ejecutando en modo script...")
        print("Para ejecutar como API, use: python scrapper.py --api\n")
        
        run_script_mode()
        
        print("\n=== FIN DEL PROCESO DE AUTOMATIZACIÓN ===\n")
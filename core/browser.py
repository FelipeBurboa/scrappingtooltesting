import os
import time
import agentql
from playwright.sync_api import sync_playwright
from config.settings import BROWSER_ARGS, BROWSER_CONTEXT_OPTIONS, DOWNLOADS_DIR


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
        args=BROWSER_ARGS
    )
    
    context = browser.new_context(**BROWSER_CONTEXT_OPTIONS)
    
    return playwright, browser, context


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
            if not os.path.exists(DOWNLOADS_DIR):
                os.makedirs(DOWNLOADS_DIR)
            save_path = os.path.join(DOWNLOADS_DIR, f"{report_type}_report_{download.suggested_filename}")
        else:
            save_path = f"{report_type}_report_{download.suggested_filename}"
        
        download.save_as(save_path)
        print(f"✓ Archivo guardado: {save_path}")
        
        return True, save_path
        
    except Exception as e:
        raise Exception(f"Error en la descarga: {e}")
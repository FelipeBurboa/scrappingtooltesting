import agentql
from core.browser import enhanced_browser_setup_fast, wait_for_agentql_element_fast
from config.settings import USER_NAME, PASSWORD, INITIAL_URL


def login(headless=False):
    """
    OPTIMIZED: Faster login with reduced waits
    """
    print("\nIniciando proceso de login (optimizado para velocidad)...")
    
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
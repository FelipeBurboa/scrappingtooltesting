import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
print("Variables de entorno cargadas correctamente")

# Environment variables
USER_NAME = os.getenv("USER_NAME")
PASSWORD = os.getenv("PASSWORD")
AGENTQL_API_KEY = os.getenv("AGENTQL_API_KEY")

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Configure AgentQL API key
os.environ["AGENTQL_API_KEY"] = AGENTQL_API_KEY

print(f"Usuario configurado: {USER_NAME}")
print("Contraseña configurada")
print("API Key de AgentQL configurada")
print(f"Entorno detectado: {ENVIRONMENT}")

# Application settings
INITIAL_URL = "https://datasharing.cencosud.com/MicroStrategyLibraryDS/auth/ui/loginPage"
DOWNLOADS_DIR = "./downloads"

# Server settings (updated to port 3000 for Coolify)
SERVER_PORT = 3000
SERVER_HOST = "0.0.0.0"

# Browser settings - Environment specific
if ENVIRONMENT in ["production", "prod", "coolify"]:
    print("🐳 Usando configuración de browser para PRODUCCIÓN (Coolify)")
    BROWSER_ARGS = [
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
else:
    print("💻 Usando configuración de browser para DESARROLLO (Windows/Local)")
    BROWSER_ARGS = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-web-security',
        '--disable-blink-features=AutomationControlled'
    ]

BROWSER_CONTEXT_OPTIONS = {
    'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'viewport': {'width': 1920, 'height': 1080},
    'accept_downloads': True,
    'java_script_enabled': True,
    'has_touch': False,
    'is_mobile': False,
    'ignore_https_errors': True
}
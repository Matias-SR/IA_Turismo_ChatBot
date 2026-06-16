import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_EMBEDDINGS_URL = os.getenv("OPENAI_EMBEDDINGS_URL")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GMAIL_REMITENTE = os.getenv("GMAIL_REMITENTE")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def validar_configuracion() -> list[str]:
    """
    Verifica la existencia de las variables de entorno necesarias.
    Retorna una lista con advertencias sobre variables faltantes.
    """
    advertencias = []
    if not OPENAI_API_KEY:
        advertencias.append("⚠️ OPENAI_API_KEY no configurada. El agente LLM y los embeddings no funcionarán.")
    if not OPENWEATHER_API_KEY:
        advertencias.append("⚠️ OPENWEATHER_API_KEY no configurada. Las consultas de clima fallarán.")
    if not GMAIL_REMITENTE or not GMAIL_APP_PASSWORD:
        advertencias.append("⚠️ Credenciales de Gmail no configuradas (GMAIL_REMITENTE, GMAIL_APP_PASSWORD). El envío de correos fallará.")
    return advertencias

import re

# Expresiones regulares para validaciones seguras
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
NOMBRE_REGEX = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s']{2,50}$")
FECHA_REGEX = re.compile(r"^[a-zA-Z0-9\s\/\-]{2,40}$")

# Listado de términos sospechosos de Prompt Injection (Firmas de jailbreak o control)
PROMPT_INJECTION_KEYWORDS = [
    "ignore previous", "ignora las instrucciones", "forget my previous", "olvida las instrucciones",
    "developer mode", "modo desarrollador", "system prompt", "system override", "jailbreak",
    "acting as", "actúa como", "you are now a", "ahora eres un", "output instructions",
    "tell me your system", "revela tu prompt", "revela tus instrucciones", "base64", "rot13",
    "decode", "código python", "run command", "ejecuta el comando", "instructions above",
    "instrucciones anteriores", "ignore all rules", "ignora todas las reglas"
]

def verificar_y_sanitizar_entrada(texto: str) -> tuple[bool, str]:
    """
    Analiza un texto de entrada del usuario para detectar intentos de Prompt Injection.
    Retorna (es_malicioso, texto_sanitizado_o_advertencia).
    """
    if not texto:
        return False, ""
    
    # 1. Sanitizar eliminando caracteres peligrosos de control o etiquetas HTML que puedan confundir al parser
    texto_sanitizado = re.sub(r"<[^>]*>", "", texto) # Eliminar etiquetas XML/HTML
    texto_sanitizado = texto_sanitizado.strip()
    
    texto_lower = texto_sanitizado.lower()
    
    # 2. Comprobar palabras clave de Prompt Injection
    for keyword in PROMPT_INJECTION_KEYWORDS:
        if keyword in texto_lower:
            mensaje_advertencia = (
                "⚠️ **Intento de manipulación detectado.**\n"
                "Como asistente virtual de 3M Tours, solo puedo ayudarte con temas de planificación turística "
                "y reservas en la Región de Los Lagos. Por favor, evita realizar solicitudes que infrinjan "
                "nuestras normas de seguridad, ya que intentos repetidos pueden resultar en la suspensión de tu sesión."
            )
            return True, mensaje_advertencia
            
    return False, texto_sanitizado

def validar_datos_reserva(nombre: str, email: str, fecha: str) -> tuple[bool, str]:
    """
    Valida los datos ingresados para la confirmación de una reserva usando expresiones regulares.
    Retorna (es_valido, mensaje_error_o_exito).
    """
    if not nombre or not NOMBRE_REGEX.match(nombre.strip()):
        return False, "❌ Nombre inválido. Debe contener entre 2 y 50 letras y espacios."
        
    if not email or not EMAIL_REGEX.match(email.strip()):
        return False, "❌ Correo electrónico inválido. Ej: cliente@gmail.com"
        
    if not fecha or not FECHA_REGEX.match(fecha.strip()):
        return False, "❌ Fecha inválida. Debe tener un formato lógico (ej. '15 de Diciembre' o '20-12-2026')."
        
    return True, "Validación exitosa"

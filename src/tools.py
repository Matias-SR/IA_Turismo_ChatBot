import os
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from langchain_core.tools import tool
from src.config import OPENWEATHER_API_KEY, GMAIL_REMITENTE, GMAIL_APP_PASSWORD
from src.security import validar_datos_reserva

# Datos de tours con precios dinámicos por persona
TOURS_INFO = {
    "puerto montt": {
        "tours": {
            "Tour Angelmó + Costanera (medio día)": 25000,
            "Tour Alerce Andino (día completo)": 45000,
            "Tour Reloncaví (medio día)": 30000
        }
    },
    "puerto varas": {
        "tours": {
            "Tour Lago Llanquihue (medio día)": 30000,
            "Tour Saltos del Petrohué (día completo)": 40000,
            "Tour Volcán Osorno (día completo)": 50000
        }
    },
    "frutillar": {
        "tours": {
            "Tour Teatro del Lago (medio día)": 35000,
            "Tour Costanera de Frutillar (medio día)": 20000,
            "Tour Cultural Alemán (medio día)": 25000
        }
    },
    "chiloe": {
        "tours": {
            "Tour Castro (medio día)": 35000,
            "Tour Iglesias Patrimoniales (día completo)": 55000,
            "Tour Pingüineras (día completo)": 60000
        }
    },
    "cochamo": {
        "tours": {
            "Trekking Valle Cochamó (día completo)": 50000,
            "Cabalgata Sendero Cochamó (día completo)": 70000
        }
    },
    "ensenada": {
        "tours": {
            "Tour Aventura Río Petrohué (medio día)": 35000,
            "Canopy La Ensenada (medio día)": 30000
        }
    }
}

# Costos de transporte detallados
TRANSPORTE_INFO = {
    "puerto montt": {
        "auto": {"duracion": "Destino local", "costos_detalle": "Vehículo propio: $0 CLP peajes"},
        "bus": {"duracion": "Destino local (micro/colectivo)", "costos_detalle": "$800 CLP por pasaje"},
        "privado": {"duracion": "15 min (transfer de la agencia)", "costos_detalle": "$15.000 CLP total"}
    },
    "puerto varas": {
        "auto": {"duracion": "30 min", "costos_detalle": "Vehículo propio: $0 CLP peajes"},
        "bus": {"duracion": "40 min (bus interurbano)", "costos_detalle": "$1.500 CLP por persona"},
        "privado": {"duracion": "30 min (transfer de la agencia)", "costos_detalle": "$25.000 CLP total"}
    },
    "frutillar": {
        "auto": {"duracion": "1h", "costos_detalle": "Vehículo propio: $0 CLP peajes"},
        "bus": {"duracion": "1h 20min (bus interurbano)", "costos_detalle": "$2.500 CLP por persona"},
        "privado": {"duracion": "1h (transfer de la agencia)", "costos_detalle": "$35.000 CLP total"}
    },
    "chiloe": {
        "auto": {"duracion": "2h 30min (incluye cruce)", "costos_detalle": "Vehículo propio: Peaje Pargua $4.500 CLP + Transbordador $15.000 CLP (cruce de auto)"},
        "bus": {"duracion": "3h", "costos_detalle": "Bus público interurbano (incluye ferry): $6.000 CLP por persona"},
        "privado": {"duracion": "2h 30min (servicio transfer de la agencia)", "costos_detalle": "$80.000 CLP total (incluye cruce y ferry)"}
    },
    "cochamo": {
        "auto": {"duracion": "2h", "costos_detalle": "Vehículo propio: $0 CLP peajes"},
        "bus": {"duracion": "2h 30min (bus local)", "costos_detalle": "$4.500 CLP por persona"},
        "privado": {"duracion": "2h (servicio transfer de la agencia)", "costos_detalle": "$60.000 CLP total"}
    },
    "ensenada": {
        "auto": {"duracion": "1h 15min", "costos_detalle": "Vehículo propio: $0 CLP peajes"},
        "bus": {"duracion": "1h 30min (bus local)", "costos_detalle": "$3.000 CLP por persona"},
        "privado": {"duracion": "1h 15min (transfer de la agencia)", "costos_detalle": "$40.000 CLP total"}
    }
}

# Variable global para guardar el retriever RAG configurado en database.py
_retriever_instancia = None

def establecer_retriever(retriever):
    global _retriever_instancia
    _retriever_instancia = retriever

@tool
def obtener_tours_y_precios(zona: str, personas: int) -> str:
    """
    Devuelve los tours disponibles en un destino con sus precios detallados.
    Calcula el costo total para la cantidad de personas y aplica un 10% de descuento
    si el número de personas es superior a 4 (> 4).
    Zonas válidas: puerto montt, puerto varas, frutillar, chiloe, cochamo, ensenada.
    """
    zona_key = zona.lower().strip()
    if zona_key not in TOURS_INFO:
        validas = ", ".join(TOURS_INFO.keys())
        return f"No tenemos registros de tours para '{zona}'. Zonas válidas: {validas}."
        
    tours = TOURS_INFO[zona_key]["tours"]
    resultado = f"🎒 **Tours disponibles en {zona.title()}:**\n"
    
    descuento_aplica = personas > 4
    
    for nombre_tour, precio_unitario in tours.items():
        costo_base_total = precio_unitario * personas
        if descuento_aplica:
            precio_con_dcto = int(precio_unitario * 0.9)
            costo_total_con_dcto = precio_con_dcto * personas
            resultado += (
                f"- **{nombre_tour}**:\n"
                f"  - Valor unitario base: ${precio_unitario:,} CLP\n"
                f"  - ¡Descuento de Grupo (10%) aplicado!: **${precio_con_dcto:,} CLP** por persona\n"
                f"  - Costo total para {personas} personas: **${costo_total_con_dcto:,} CLP** (Ahorro de ${costo_base_total - costo_total_con_dcto:,} CLP)\n"
            )
        else:
            resultado += (
                f"- **{nombre_tour}**:\n"
                f"  - Valor por persona: ${precio_unitario:,} CLP\n"
                f"  - Costo total para {personas} personas: **${costo_base_total:,} CLP**\n"
            )
    return resultado

@tool
def obtener_transporte_y_peajes(zona: str, medio_transporte: str) -> str:
    """
    Entrega el detalle de opciones de transporte desde Puerto Montt hacia el destino seleccionado.
    Permite recomendar transporte privado si está disponible, detallar peajes para vehículo propio,
    o rutas de transporte público en su defecto.
    Parámetros:
    - zona: destino turistico (puerto montt, puerto varas, frutillar, chiloe, cochamo, ensenada).
    - medio_transporte: tipo de movilización ('auto' para propio, 'bus' para público, 'privado' para transfer de la agencia).
    """
    zona_key = zona.lower().strip()
    medio_key = medio_transporte.lower().strip()
    
    if zona_key not in TRANSPORTE_INFO:
        return f"No hay información de transporte disponible para '{zona}'."
        
    medios_disponibles = TRANSPORTE_INFO[zona_key]
    
    if medio_key not in medios_disponibles:
        validos = ", ".join(medios_disponibles.keys())
        return f"Medio de transporte '{medio_transporte}' no válido para esta zona. Medios válidos: {validos}."
        
    info = medios_disponibles[medio_key]
    
    resultado = f"🚌 **Información de Transporte hacia {zona.title()} ({medio_transporte.upper()}):**\n"
    resultado += f"- 🕒 **Duración estimada:** {info['duracion']}\n"
    resultado += f"- 💰 **Detalle de Costos/Ruta:** {info['costos_detalle']}\n"
    
    if medio_key == "privado":
        resultado += "*(Servicio de van privada de la agencia. Debe reservarse con anticipación)*\n"
    elif medio_key == "auto":
        resultado += "*(Recuerda considerar el combustible adicional para el trayecto)*\n"
        
    return resultado

@tool
def consultar_clima(zona: str) -> str:
    """
    Consulta el clima actual de un destino en tiempo real usando OpenWeatherMap
    y sugiere ropa/vestimenta adecuada en base a las condiciones y temperatura.
    Zonas válidas: puerto montt, puerto varas, frutillar, chiloe, cochamo, ensenada.
    """
    ciudades = {
        "puerto montt": "Puerto Montt,CL",
        "puerto varas": "Puerto Varas,CL",
        "frutillar":    "Frutillar,CL",
        "chiloe":       "Castro,CL",
        "cochamo":      "Cochamo,CL",
        "ensenada":     "Ensenada,CL"
    }

    zona_key = zona.lower().strip()
    ciudad = ciudades.get(zona_key)
    
    if not ciudad:
        return f"No se puede consultar el clima para '{zona}'. Zonas válidas: {', '.join(ciudades.keys())}."
        
    if not OPENWEATHER_API_KEY:
        # Clima mock fallback si no hay API key para que no se caiga
        return (
            f"🌤️ Clima actual en {zona.title()} (Simulado - OPENWEATHER_API_KEY faltante):\n"
            f"  - Descripción : Parcialmente despejado\n"
            f"  - Temperatura : 12°C\n"
            f"  - Viento      : 10 km/h\n"
            f"  - Vestimenta sugerida: Vestir en capas (polera, chaleco o polar y cortaviento liviano)."
        )
        
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": ciudad,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "es",
        }
        resp = requests.get(url, params=params, timeout=8)
        
        if resp.status_code != 200:
            return f"❌ Error al consultar el clima (HTTP {resp.status_code}): {resp.json().get('message', 'sin detalle')}"
            
        data = resp.json()
        descripcion = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        sensacion = data["main"]["feels_like"]
        humedad = data["main"]["humidity"]
        viento_kmh = round(data["wind"]["speed"] * 3.6, 1)
        
        # Evaluar lluvia
        lluvia = "rain" in data or any(
            w in descripcion.lower() for w in ["lluvia", "llovizna", "chubascos", "tormenta", "nieve"]
        )
        
        # Sugerencia de ropa y advertencia de clima
        if lluvia:
            evaluacion = "⚠️ **Lluvia/Tormenta detectada:** Se recomiendan tours bajo techo y actividades cubiertas."
            ropa = "🧥 **Ropa sugerida:** Impermeable completo, chaqueta impermeable gruesa, calzado de trekking resistente al agua (gore-tex) y paraguas."
        elif temp < 8:
            evaluacion = "🥶 **Bajas temperaturas detectadas:** Clima bastante frío."
            ropa = "🧥 **Ropa sugerida:** Primera capa térmica (calzas/camiseta), gorro de lana, guantes térmicos, bufanda y una parka de abrigo."
        elif temp >= 18:
            evaluacion = "☀️ **Condiciones agradables detectadas:** Excelente día para actividades al aire libre."
            ropa = "🧢 **Ropa sugerida:** Polera manga corta, cortavientos ligero por si corre viento, gorro para el sol, lentes de sol y bloqueador solar."
        else:
            evaluacion = "🌤️ **Clima templado/fresco:** Aceptable para realizar la mayoría de los tours."
            ropa = "🧥 **Ropa sugerida:** Vestir en capas (polera, un polar o chaleco intermedio, y cortavientos liviano)."

        return (
            f"🌦️ **Clima actual en {zona.title()}:**\n"
            f"  - Condición   : {descripcion}\n"
            f"  - Temperatura : {temp}°C (Sensación térmica de {sensacion}°C)\n"
            f"  - Humedad     : {humedad}%\n"
            f"  - Viento      : {viento_kmh} km/h\n"
            f"  - Estado      : {evaluacion}\n"
            f"  - Vestimenta  : {ropa}"
        )
    except Exception as e:
        return f"❌ Error de conexión al servicio meteorológico: {str(e)}"

@tool
def consultar_documentos_empresa(query: str) -> str:
    """
    Realiza una búsqueda semántica en la base de datos RAG corporativa de 3M Tours.
    Útil para responder preguntas institucionales, políticas de cancelación, soporte y preguntas frecuentes.
    """
    if _retriever_instancia is None:
        return "❌ Error: El motor RAG no ha sido inicializado en este agente."
        
    try:
        docs = _retriever_instancia.get_relevant_documents(query)
        if not docs:
            return "No se encontró información relevante sobre este tema en los documentos corporativos de 3M Tours."
            
        respuesta = "📄 **Información corporativa encontrada:**\n\n"
        for i, doc in enumerate(docs):
            respuesta += f"**{doc.metadata.get('title', 'Documento')}**:\n{doc.page_content}\n\n"
        return respuesta
    except Exception as e:
        return f"❌ Error al consultar la base de datos de la empresa: {str(e)}"

@tool
def enviar_confirmacion_email(
    email_cliente: str,
    nombre_cliente: str,
    tours: str,
    fecha: str,
    personas: int,
    zona: str,
    transporte_elegido: str,
    costo_transporte: int = 0
) -> str:
    """
    Envía un correo de confirmación formal al cliente con el resumen y desglose de su itinerario.
    
    Parámetros:
    - email_cliente: correo del cliente (debe ser válido).
    - nombre_cliente: nombre del cliente.
    - tours: tours reservados (texto libre descriptivo).
    - fecha: fecha del viaje.
    - personas: cantidad de pasajeros.
    - zona: destino turistico.
    - transporte_elegido: medio de transporte (auto, bus, privado).
    - costo_transporte: costo adicional del transporte propio/peajes (opcional, en CLP).
    """
    # Validar entradas con security.py
    valido, msg_error = validar_datos_reserva(nombre_cliente, email_cliente, fecha)
    if not valido:
        return f"❌ Error de validación: {msg_error}"

    if not GMAIL_REMITENTE or not GMAIL_APP_PASSWORD:
        return (
            "❌ Error: Las credenciales de correo (GMAIL_REMITENTE, GMAIL_APP_PASSWORD) "
            "no están configuradas en el archivo .env."
        )

    # Buscar valores base
    zona_key = zona.lower().strip()
    valor_tours = 0
    tours_list = [t.strip().lower() for t in tours.split(",")]
    
    if zona_key in TOURS_INFO:
        tours_dict = TOURS_INFO[zona_key]["tours"]
        for tour_reservado in tours_list:
            for nombre_tour, precio_unitario in tours_dict.items():
                if nombre_tour.lower() in tour_reservado or tour_reservado in nombre_tour.lower():
                    valor_tours += precio_unitario
                    break
                    
    if valor_tours == 0:
        # Fallback si no coincide el nombre exacto
        valor_tours = 40000 

    descuento_aplica = personas > 4
    if descuento_aplica:
        valor_tours_total = int(valor_tours * 0.9 * personas)
        descuento_txt = "10% aplicado (Grupo > 4 personas)"
    else:
        valor_tours_total = valor_tours * personas
        descuento_txt = "No aplica"

    costo_final_total = valor_tours_total + costo_transporte

    html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; padding: 10px;">
      <div style="background: #1e3a8a; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; color: white;">
        <h1 style="margin: 0; font-size: 24px;">🌿 3M Tours</h1>
        <p style="color: #bfdbfe; margin: 4px 0;">Reserva Confirmada de Itinerario</p>
      </div>
      <div style="background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px;">
        <p>Estimado/a <strong>{nombre_cliente}</strong>,</p>
        <p>Nos complace informarte que tu itinerario ha sido agendado con éxito. A continuación, te presentamos el detalle de tu reserva:</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 18px 0;">
          <tr style="background: #eff6ff;">
            <td style="padding: 10px; border: 1px solid #bfdbfe; font-weight: bold; width: 35%;">📍 Destino</td>
            <td style="padding: 10px; border: 1px solid #bfdbfe;">{zona.title()}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">🗓️ Fecha</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">{fecha}</td>
          </tr>
          <tr style="background: #eff6ff;">
            <td style="padding: 10px; border: 1px solid #bfdbfe; font-weight: bold;">🎒 Tours</td>
            <td style="padding: 10px; border: 1px solid #bfdbfe;">{tours}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">👥 Viajeros</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">{personas} persona(s)</td>
          </tr>
          <tr style="background: #eff6ff;">
            <td style="padding: 10px; border: 1px solid #bfdbfe; font-weight: bold;">🚌 Transporte</td>
            <td style="padding: 10px; border: 1px solid #bfdbfe;">{transporte_elegido.title()}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">🏷️ Descuento</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0; color: #16a34a;">{descuento_txt}</td>
          </tr>
          <tr style="background: #f1f5f9; font-size: 16px;">
            <td style="padding: 12px; border: 1px solid #cbd5e1; font-weight: bold;">💰 Costo Total</td>
            <td style="padding: 12px; border: 1px solid #cbd5e1; color: #1e3a8a; font-weight: bold;">${costo_final_total:,} CLP</td>
          </tr>
        </table>

        <div style="background: #fffbeb; padding: 14px; border-left: 4px solid #d97706; border-radius: 4px; margin: 16px 0;">
          ⚠️ **Instrucciones Importantes:**
          Presentarse 15 minutos antes de la hora indicada en el punto de encuentro. Llevar ropa cómoda adaptada a las condiciones climáticas del día.
        </div>

        <p style="text-align: center; margin-top: 24px; color: #64748b; font-size: 14px;">
          ¡Muchas gracias por confiar en 3M Tours para tu viaje! 🏔️🌊
        </p>
      </div>
      <p style="text-align: center; font-size: 11px; color: #94a3b8; margin-top: 12px;">
        3M Tours — Puerto Montt, Región de Los Lagos, Chile
      </p>
    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✅ Reserva Confirmada: Tour en {zona.title()} — 3M Tours"
        msg["From"] = GMAIL_REMITENTE
        msg["To"] = email_cliente
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_REMITENTE, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_REMITENTE, email_cliente, msg.as_string())

        return (
            f"✅ Correo de confirmación enviado exitosamente a {email_cliente}.\n"
            f"Resumen: {personas} personas — {zona.title()} — Costo: ${costo_final_total:,} CLP."
        )
    except smtplib.SMTPAuthenticationError:
        return (
            "❌ Error de autenticación en Gmail. Verifica tus credenciales GMAIL_REMITENTE y GMAIL_APP_PASSWORD."
        )
    except Exception as e:
        return f"❌ Error al enviar el correo: {str(e)}"

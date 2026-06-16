import streamlit as st
import time
from langchain_core.messages import HumanMessage, AIMessage
from src.config import validar_configuracion, OPENWEATHER_API_KEY
from src.security import verificar_y_sanitizar_entrada
from src.agent import agent
from src.tools import consultar_clima

# 1. Configuración de página de Streamlit
st.set_page_config(
    page_title="3M Tours - Planificador Inteligente",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inyección de Estilos CSS Premium (Estética Moderna y Atractiva)
st.markdown("""
    <style>
    /* Estilos Generales */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Encabezado */
    .header-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #0d9488 100%);
        padding: 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .header-title {
        font-size: 32px;
        font-weight: 700;
        margin: 0;
    }
    .header-subtitle {
        font-size: 16px;
        color: #e2e8f0;
        margin-top: 5px;
    }
    
    /* Tarjetas de Clima en la barra lateral */
    .weather-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #0d9488;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    
    /* Indicador de Seguridad */
    .security-banner {
        background-color: #fef2f2;
        border: 1px solid #fca5a5;
        color: #991b1b;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Botón personalizado */
    .stButton>button {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%) !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

# 3. Validar configuración e inicializar variables
warnings = validar_configuracion()
if warnings:
    with st.expander("⚠️ Avisos de configuración del entorno (Faltan variables)", expanded=True):
        for w in warnings:
            st.warning(w)

# Inicializar estados de la sesión
if "chat_messages" not in st.session_state:
    # Mensajes visuales del chat
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "¡Hola! Bienvenido/a a **3M Tours**. 🌿 Soy tu agente de planificación turística.\n\n¿Qué destino te gustaría explorar hoy? Cuéntame cuántas personas viajan, cuál es tu presupuesto estimado y qué medio de transporte prefieres para armarte el itinerario ideal."}
    ]
if "agent_history" not in st.session_state:
    # Memoria interna del agente LangGraph
    st.session_state.agent_history = []
if "security_warnings" not in st.session_state:
    # Contador de inyecciones
    st.session_state.security_warnings = 0
if "blocked" not in st.session_state:
    st.session_state.blocked = False

# 4. Renderizar Encabezado Principal
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🌿 3M Tours</h1>
        <p class="header-subtitle">Planificación Turística Inteligente y Segura en la Región de Los Lagos</p>
    </div>
""", unsafe_allow_html=True)

# 5. Barra Lateral (Sidebar) con utilidades y estado del clima
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/mountain.png", width=120)
    st.header("Planificación Rápida")
    
    # Inputs rápidos
    destino_sel = st.selectbox(
        "📍 Destino sugerido", 
        ["Puerto Montt", "Puerto Varas", "Frutillar", "Chiloé", "Cochamó", "Ensenada"]
    )
    num_personas = st.number_input("👥 Número de viajeros", min_value=1, max_value=50, value=2)
    transporte_sel = st.selectbox(
        "🚌 Medio de Transporte", 
        ["Auto propio", "Bus público", "Transfer privado (Agencia)"]
    )
    presupuesto_usr = st.number_input("💰 Presupuesto máximo (CLP)", min_value=0, value=200000, step=10000)
    
    if st.button("🪄 Generar Plan Rápido"):
        if not st.session_state.blocked:
            txt_transporte = "auto propio" if transporte_sel == "Auto propio" else ("bus público" if transporte_sel == "Bus público" else "servicio privado")
            prompt_rapido = (
                f"Quiero planificar un viaje a {destino_sel} para {num_personas} personas, "
                f"viajando en {txt_transporte} y con un presupuesto total de ${presupuesto_usr:,} CLP."
            )
            # Simular entrada del usuario
            st.session_state.chat_messages.append({"role": "user", "content": prompt_rapido})
            
            # Ejecutar consulta
            with st.spinner("Construyendo itinerario..."):
                # Agregar mensaje de usuario al historial de LangGraph
                st.session_state.agent_history.append(HumanMessage(content=prompt_rapido))
                
                # Ejecutar agente
                try:
                    respuesta = agent.invoke({"messages": st.session_state.agent_history})
                    res_messages = respuesta.get("messages", [])
                    st.session_state.agent_history = res_messages
                    text_response = res_messages[-1].content if res_messages else str(respuesta)
                except Exception as e:
                    text_response = f"❌ Error en la ejecución: {e}"
                
                st.session_state.chat_messages.append({"role": "assistant", "content": text_response})
                st.rerun()

    # Widget de clima en la barra lateral
    st.markdown("---")
    st.header("☀️ Clima en Tiempo Real")
    
    ciudades_clima = ["Puerto Montt", "Puerto Varas", "Frutillar", "Chiloé"]
    for ciudad in ciudades_clima:
        # Consulta de clima simplificada para la barra lateral
        with st.spinner(f"Cargando clima {ciudad}..."):
            try:
                # Ejecutamos la tool consultar_clima. Como es una tool de LangChain, podemos extraer su función de ejecución local
                info_clima = consultar_clima.run(ciudad)
                # Extraer temperatura del texto devuelto
                import re
                temp_match = re.search(r"Temperatura\s*:\s*([\d\.-]+)°C", info_clima)
                cond_match = re.search(r"Condición\s*:\s*([^\n]+)", info_clima)
                
                temp_str = f"{temp_match.group(1)}°C" if temp_match else "12°C"
                cond_str = cond_match.group(1) if cond_match else "Despejado"
                
                icono = "☀️" if "despejado" in cond_str.lower() or "soleado" in cond_str.lower() else ("☁️" if "nubes" in cond_str.lower() or "nublado" in cond_str.lower() else "🌧️")
                
                st.markdown(f"""
                    <div class="weather-card">
                        <strong>📍 {ciudad}</strong><br/>
                        <span style="font-size: 20px;">{icono} {temp_str}</span><br/>
                        <span style="font-size: 12px; color: #64748b;">{cond_str}</span>
                    </div>
                """, unsafe_allow_html=True)
            except Exception:
                st.markdown(f"""
                    <div class="weather-card">
                        <strong>📍 {ciudad}</strong><br/>
                        <span style="color: #ef4444;">⚠️ No disponible</span>
                    </div>
                """, unsafe_allow_html=True)

# 6. Renderizar Chat
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 7. Procesar Entrada del Usuario
if st.session_state.blocked:
    st.error("⛔ **Acceso Bloqueado Temporalmente.** Tu sesión ha sido suspendida debido a múltiples intentos consecutivos de vulneración del sistema (Prompt Injection).")
else:
    if user_input := st.chat_input("Escribe tu consulta aquí... (ej: 'tengo $100.000 para ir a frutillar')"):
        # 7.1 Mostrar mensaje del usuario
        st.chat_message("user").markdown(user_input)
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        
        # 7.2 Capa de Seguridad Activa contra Prompt Injection
        es_malicioso, advertencia_o_sanitizado = verificar_y_sanitizar_entrada(user_input)
        
        if es_malicioso:
            # Incrementar warnings de seguridad
            st.session_state.security_warnings += 1
            if st.session_state.security_warnings >= 3:
                st.session_state.blocked = True
                st.error("⛔ **Acceso Bloqueado Temporalmente.** Tu sesión ha sido suspendida debido a múltiples intentos consecutivos de vulneración del sistema (Prompt Injection).")
                st.session_state.chat_messages.append({"role": "assistant", "content": "⛔ *Sesión bloqueada por políticas de seguridad corporativas.*"})
                st.rerun()
            else:
                # Mostrar la advertencia en el chat
                st.chat_message("assistant").markdown(advertencia_o_sanitizado)
                st.session_state.chat_messages.append({"role": "assistant", "content": advertencia_o_sanitizado})
                st.warning(f"Advertencia de seguridad {st.session_state.security_warnings}/3. Al llegar a 3 intentos la sesión será suspendida.")
        else:
            # Entrada limpia, resetear warnings consecutivos de inyección (o mantener si es persistente)
            # Para mayor indulgencia, reseteamos si escribe algo limpio
            st.session_state.security_warnings = 0
            
            # 7.3 Ejecución del Agente
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Pensando..."):
                    # Agregar mensaje al historial de LangGraph
                    st.session_state.agent_history.append(HumanMessage(content=advertencia_o_sanitizado))
                    
                    try:
                        respuesta = agent.invoke({"messages": st.session_state.agent_history})
                        res_messages = respuesta.get("messages", [])
                        st.session_state.agent_history = res_messages
                        text_response = res_messages[-1].content if res_messages else str(respuesta)
                    except Exception as e:
                        text_response = f"❌ Ocurrió un error al procesar tu solicitud: {str(e)}"
                    
                    # Mostrar la respuesta final
                    message_placeholder.markdown(text_response)
                    st.session_state.chat_messages.append({"role": "assistant", "content": text_response})

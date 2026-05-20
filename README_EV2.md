# 🌿 3M Tours — Agente de IA para Planificación Turística

> Agente conversacional de inteligencia artificial que planifica itinerarios turísticos personalizados en la Región de Los Lagos, adaptados al clima en tiempo real.

---

## 📋 Índice

1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Arquitectura General del Agente](#2-arquitectura-general-del-agente)
3. [Frameworks e Integración Técnica (IE2)](#3-frameworks-e-integración-técnica-ie2)
4. [Memoria de Contenido (IE3)](#4-memoria-de-contenido-ie3)
5. [Recuperación de Contexto Semántico (IE4)](#5-recuperación-de-contexto-semántico-ie4)
6. [Planificación de Tareas (IE5)](#6-planificación-de-tareas-ie5)
7. [Toma de Decisiones Autónoma (IE6)](#7-toma-de-decisiones-autónoma-ie6)
8. [Herramientas del Agente (IE1)](#8-herramientas-del-agente-ie1)
9. [Justificación de Componentes (IE8)](#9-justificación-de-componentes-ie8)
10. [Configuración del Entorno](#10-configuración-del-entorno)
11. [Resumen de Criterios Evaluados](#11-resumen-de-criterios-evaluados)

---

## 1. Descripción del Proyecto

**3M Tours** es una agencia de turismo ubicada en Puerto Montt, especializada en recorridos por la Región de Los Lagos. Este proyecto implementa un agente conversacional de IA capaz de:

- Consultar el clima en tiempo real de cada destino turístico
- Recomendar paquetes de tours adaptados al clima y al tiempo disponible del cliente
- Calcular precios según el número de personas
- Informar sobre opciones de transporte (auto, bus y ferry/transbordador)
- Generar y enviar un itinerario personalizado por correo electrónico al confirmar la reserva

| Campo | Detalle |
|---|---|
| Proyecto | Agente IA 3M Tours |
| Versión | 1.0.0 |
| Ubicación | Puerto Montt, Región de Los Lagos, Chile |
| Tecnologías | Python · LangChain · LangGraph · GPT-4o-mini · OpenWeatherMap |

---

## 2. Arquitectura General del Agente

El agente sigue una arquitectura **ReAct (Reasoning + Acting)**, implementada con **LangGraph**. El modelo razona sobre la consulta del cliente, selecciona autónomamente las herramientas necesarias, ejecuta las acciones y formula una respuesta coherente.

### Diagrama de Orquestación (IE7)

```
  👤  Cliente (terminal / interfaz)
         │  HumanMessage
         ▼
  ┌──────────────────────────────────┐
  │   LangGraph ReAct Agent          │
  │   GPT-4o-mini (OpenAI)           │
  └───┬──────────┬───────────┬───────┘
      │          │           │
  ┌───▼────┐ ┌──▼─────┐ ┌───▼───────────┐
  │clima   │ │paquetes│ │opciones       │
  │_zona() │ │_turist.│ │_transporte()  │
  └───┬────┘ └──┬─────┘ └───┬───────────┘
      │    +    │    +       │
  ┌───▼─────────▼────────────▼──────────┐
  │  precio_tour()  +  enviar_email()   │
  └─────────────────────────────────────┘
         │  AIMessage
         ▼
  📧  Correo de confirmación + Respuesta al cliente
```

### Flujo de decisión interno

```
Cliente escribe consulta
        │
        ▼
¿Menciona un destino?
   ├── Sí → clima_zona() → paquetes_turisticos() → opciones_transporte()
   │         └── Armar itinerario según clima y días disponibles
   └── No → Solicitar destino o responder pregunta puntual
        │
        ▼
¿Cliente confirma el tour?
   ├── Sí → Pedir nombre, email, fecha, transporte → enviar_confirmacion_email()
   └── No → Continuar conversación
```

---

## 3. Frameworks e Integración Técnica (IE2)

El agente integra los siguientes frameworks, seleccionados por su escalabilidad y compatibilidad técnica:

| Componente | Propósito | Versión / API |
|---|---|---|
| **LangGraph** | Orquestación del agente ReAct con manejo de estado y grafo de decisiones | `langgraph >= 0.2` |
| **LangChain** | Abstracción de tools, prompts y cadenas de procesamiento | `langchain >= 0.3` |
| **LangChain-OpenAI** | Conector entre LangChain y la API de OpenAI | `langchain-openai` |
| **OpenAI GPT-4o-mini** | Modelo de lenguaje para razonamiento y generación de respuestas | `gpt-4o-mini` |
| **OpenWeatherMap** | API REST para consulta de clima en tiempo real | `v2.5 /weather` |
| **smtplib** (stdlib) | Envío de correos HTML por SMTP SSL con Gmail | Python stdlib |
| **python-dotenv** | Carga segura de variables de entorno desde archivo `.env` | `dotenv >= 1.0` |

---

## 4. Memoria de Contenido (IE3)

El agente mantiene continuidad conversacional a través de un historial acumulativo de mensajes. Cada turno agrega el mensaje del cliente y la respuesta del agente al arreglo `conversation_history`, que se pasa completo al siguiente `invoke()`:

```python
# Agregar mensaje del cliente
conversation_history.append(HumanMessage(content=pregunta))

# Invocar al agente con el historial completo
respuesta = agent.invoke({"messages": conversation_history})

# Actualizar historial con todos los mensajes del turno (incluye ToolMessages)
conversation_history = respuesta.get("messages", [])
```

Esto permite al cliente hacer preguntas de seguimiento como:
- _"¿y si voy en bus?"_
- _"añade una persona más"_
- _"¿cuánto costaría para 4 personas?"_

...sin perder el contexto de la zona, los tours o el clima consultados previamente. LangGraph gestiona internamente el estado del grafo entre iteraciones de herramientas.

---

## 5. Recuperación de Contexto Semántico (IE4)

El contexto semántico se preserva mediante dos mecanismos complementarios:

### 5.1 System Prompt estructurado

El prompt del sistema define el rol, las instrucciones de comportamiento y el orden de uso de herramientas, estableciendo el marco semántico en el que opera el agente durante toda la sesión.

```python
SYSTEM_PROMPT = """
Eres un asistente virtual de 3M Tours, una agencia de turismo de Puerto Montt.
Cuando el cliente mencione un destino, debes:
1. Consultar el clima actual con `clima_zona`.
2. Listar los paquetes con `paquetes_turisticos`.
...
"""
```

### 5.2 Historial completo de mensajes

El arreglo `conversation_history` acumula todos los intercambios:
- `HumanMessage` — mensajes del cliente
- `AIMessage` — respuestas del agente
- `ToolMessage` — resultados de cada herramienta ejecutada

Esto permite al modelo recuperar referencias anteriores (zona mencionada, número de personas, transporte elegido) sin que el cliente deba repetirlas.

---

## 6. Planificación de Tareas (IE5)

El System Prompt define explícitamente el esquema de secuenciación que el agente debe seguir al recibir una consulta de destino:

1. Consultar el clima actual con `clima_zona()`
2. Listar paquetes disponibles con `paquetes_turisticos()`
3. Mostrar opciones de transporte con `opciones_transporte()`
4. Considerar el tiempo disponible mencionado por el cliente
5. Construir el itinerario día a día, adaptado al clima
6. Si el cliente confirma: recopilar datos y ejecutar `enviar_confirmacion_email()`

Esta secuencia garantiza que el agente **nunca entregue un itinerario sin antes verificar el clima**, ni recomiende transporte sin consultar las opciones disponibles.

---

## 7. Toma de Decisiones Autónoma (IE6)

El agente demuestra autonomía mediante reglas condicionales integradas en el System Prompt y en la lógica de las herramientas:

| Condición del entorno | Acción autónoma del agente |
|---|---|
| Lluvia o tormenta detectada | Filtra tours y prioriza los cubiertos o de interior |
| Temperatura < 8°C | Advierte al cliente y sugiere ropa abrigada en el itinerario |
| Temperatura ≥ 18°C (día soleado) | Prioriza tours al aire libre como volcanes y lagos |
| Cliente menciona "tengo 1 día" | Arma itinerario combinando un tour de medio día y uno completo |
| Cliente menciona "tengo 2 días" | Distribuye tours entre días y zonas distintas |
| Cliente confirma el tour | Solicita datos personales y ejecuta `enviar_confirmacion_email()` |
| Zona no registrada | Informa zonas válidas sin interrumpir la conversación |

### Ejemplo de comportamiento

```
Cliente: "quiero ir a Chiloé, tengo 2 días y somos 3 personas"

Agente:
  [1] clima_zona("chiloe")         → ☀️ 17°C, viento leve
  [2] paquetes_turisticos("chiloe") → Tour Castro, Iglesias, Pingüineras
  [3] opciones_transporte("chiloe") → Auto 2h30 / Bus 3h / Ferry Pargua-Chacao

  Decisión autónoma:
  - Clima favorable → prioriza tours al aire libre
  - 2 días disponibles → distribuye en 2 jornadas
  - 3 personas → calcula $150.000 CLP total

  Respuesta: Itinerario de 2 días con tours distribuidos y opciones de transporte.
```

---

## 8. Herramientas del Agente (IE1)

El agente ejecuta acciones específicas mediante **6 herramientas** configuradas con el decorador `@tool` de LangChain. El modelo selecciona autónomamente cuál(es) usar en cada turno:

| Herramienta | Descripción | Fuente de datos |
|---|---|---|
| `clima_zona(zona)` | Consulta temperatura, descripción y viento en tiempo real | OpenWeatherMap API REST |
| `paquetes_turisticos(zona)` | Devuelve tours disponibles con duración estimada | Datos locales (dict) |
| `opciones_transporte(zona)` | Informa auto, bus y ferry desde Puerto Montt con tiempos y costos | Datos locales (dict) |
| `precio_tour(personas)` | Calcula el costo total ($50.000 CLP/persona) | Cálculo matemático |
| `informacion_3m_tours(texto)` | Entrega descripción general de la agencia | Texto estático |
| `enviar_confirmacion_email(...)` | Envía correo HTML de confirmación vía SMTP SSL | smtplib + MIME |

### Ejemplo de definición de herramienta

```python
@tool
def clima_zona(zona: str) -> str:
    """
    Consulta el clima actual de una zona turística usando OpenWeatherMap.
    Zonas válidas: puerto montt, puerto varas, chiloe, frutillar.
    """
    ...
    resp = requests.get(url, params={"q": ciudad, "appid": OPENWEATHER_API_KEY, ...})
    ...
```

---

## 9. Justificación de Componentes (IE8)

Cada componente fue seleccionado por su alineación directa con los requerimientos del flujo de trabajo:

- **LangGraph sobre LangChain puro:** permite ciclos de razonamiento (el agente puede llamar múltiples herramientas en una sola consulta) y gestión de estado entre turnos, esencial para itinerarios multi-día.

- **GPT-4o-mini:** equilibrio óptimo entre capacidad de razonamiento y costo operacional. Soporta _function calling_ nativo, base del mecanismo de `@tool`.

- **OpenWeatherMap API gratuita:** cobertura completa de todas las zonas objetivo (Puerto Montt, Puerto Varas, Castro, Frutillar) con datos en español y actualizaciones frecuentes.

- **smtplib nativo de Python:** elimina dependencias externas para el envío de correos. SMTP SSL garantiza seguridad de credenciales en tránsito.

- **python-dotenv:** estándar de la industria para separar configuración de código, previniendo la exposición de API keys en repositorios públicos.

---

## 10. Configuración del Entorno

### Instalación de dependencias

```bash
pip install langchain langchain-openai langgraph openai requests python-dotenv
```

### Variables de entorno (`.env`)

```env
OPENAI_API_KEY=sk-...
OPENWEATHER_API_KEY=tu_key_openweathermap
GMAIL_REMITENTE=tu_correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> ⚠️ Agrega `.env` a tu `.gitignore` para no exponer credenciales en GitHub.

### Estructura del proyecto

```
3m-tours/
├── 3m_tours_agent.py   # Agente principal
├── .env                # Variables de entorno (NO subir a GitHub)
├── .gitignore
└── README.md           # Este archivo
```

### Ejecución

```bash
python 3m_tours_agent.py
```

---

## 11. Resumen de Criterios Evaluados

| Criterio | Descripción | Sección |
|---|---|---|
| **IE1** | Herramientas configuradas con `@tool` — el agente ejecuta acciones con autonomía | §8 |
| **IE2** | Integración de LangGraph, LangChain, OpenAI y OpenWeatherMap | §3 |
| **IE3** | Memoria mediante `conversation_history` acumulativo entre turnos | §4 |
| **IE4** | Contexto semántico preservado por system prompt + historial completo | §5 |
| **IE5** | Esquema de planificación de 6 pasos definido en el system prompt | §6 |
| **IE6** | Toma de decisiones según clima, tiempo disponible y confirmación | §7 |
| **IE7** | Diagrama de orquestación de componentes incluido en este README | §2 |
| **IE8** | Justificación de cada componente frente a los requerimientos | §9 |
| **IE9** | Informe técnico con diagramas, flujos y decisiones de diseño | Este documento |
| **IE10** | Lenguaje técnico con evidencia concreta: código, tablas y ejemplos | Todo el documento |

---

*3M Tours — Puerto Montt, Chile*

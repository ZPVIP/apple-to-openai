# API compatible con OpenAI de Apple Intelligence

Se trata de un servidor API ligero que expone el modelo de base de Apple (Apple Intelligence) en el dispositivo a través de un punto de final de chat compatible con OpenAI. Cualquier cliente que utilice el protocolo OpenAI —interfaces de ChatGPT, plugins de IDE, herramientas CLI— puede conectarse y utilizar Apple Intelligence, que funciona completamente en tu Mac.

## Características

- Punto de final `/v1/chat/completions` **compatible con OpenAI** (con y sin streaming)
- Punto de final `/v1/models` para el descubrimiento de modelos
- **100 % en el dispositivo**: sin claves API, sin nube, sin coste por token
- **CORS habilitado**: funciona con clientes basados en navegador
- Ejecución mediante un único comando `uv run`

---

## Requisitos previos

| Requisito | Detalles |
|---|---|---|
| **Mac** | Apple Silicon (M1 o posterior) |
| **macOS** | Tahoe **26.0** o posterior |
| **Xcode** | **26.0** o posterior (acepta el acuerdo de Xcode y los SDK de Apple) |
| **RAM** | 8 GB mínimo (16 GB recomendado) |
| **Almacenamiento** | ≥ 7 GB libres para descargar el modelo en el dispositivo |
| **Python** | 3.13+ |

### 1. Habilitar Apple Intelligence

1. Abre **Ajustes del Sistema** → **Apple Intelligence y Siri**.
2. Haz clic en **Activar Apple Intelligence**.
3. Espera a que el modelo en el dispositivo termine de descargarse (mantén tu Mac conectada a Wi-Fi y a la corriente).
4. Asegúrate de que el idioma de Siri esté configurado en un idioma compatible (por ejemplo, inglés).

> **Nota:** Si la opción está desactivada, asegúrate de que tu Mac cumple todos los requisitos de hardware y está ejecutando una versión compatible de macOS. En algunas regiones, es posible que necesites configurar tu región como "Estados Unidos" en **Ajustes del Sistema → General → Idioma y región**.

---

## Configuración del entorno (desde cero)

### 2. Instalar Xcode

Descarga [Xcode 26.0+](https://developer.apple.com/xcode/) desde la Mac App Store o el sitio web de Apple Developer. Tras la instalación, abre Xcode una vez y acepta el acuerdo de licencia.

Luego, instala las herramientas de línea de comandos:

```bash
xcode-select --install
```

### 3. Instalar Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Tras la instalación, sigue las instrucciones que se muestran para añadir Homebrew a tu `PATH` (normalmente, esto implica añadir una línea a `~/.zprofile`).

### 4. Instalar Python 3.13+

```bash
brew install python@3.13
```

Verifica:

```bash
python3 --version   # Debe imprimir 3.13.x o posterior
```

### 5. Instalar `uv` (gestor de proyectos Python recomendado)

```bash
brew install uv
```

O mediante el instalador autónomo:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verifica:

```bash
uv --version
```

---

## Instalación

Crearemos un directorio de trabajo en tu carpeta de inicio y configuraremos tanto el SDK de Apple Foundation Models como este servidor API.

### 6. Clonar el SDK de Apple Foundation Models

El SDK **no** está disponible en PyPI, por lo que debe ser compilado desde el origen. Solo necesitas clonarlo aquí; el proyecto API lo compilará e instalará automáticamente en el siguiente paso.

```bash
mkdir -p ~/apple-intelligence && cd ~/apple-intelligence

git clone https://github.com/apple/python-apple-fm-sdk
```

### 7. Clonar y configurar este proyecto

```bash
cd ~/apple-intelligence

git clone https://github.com/ZPVIP/apple-to-openai
cd apple-to-openai

uv sync
```

`uv sync` realizará las siguientes acciones:
1. Crea un `.venv` en el directorio del proyecto
2. Compila e instala automáticamente el SDK desde el directorio hermano `../python-apple-fm-sdk` (configurado como una dependencia de ruta en `pyproject.toml`)
3. Instala todas las demás dependencias (`fastapi`, `uvicorn`, etc.)

La estructura de tu directorio debería ser la siguiente:

```
~/apple-intelligence/
├── python-apple-fm-sdk/          # SDK oficial de Apple (clonado en el paso 6)
└── apple-to-openai/                 # Este proyecto (clonado en el paso 7)
```

---

## Ejecutar el servidor

### Opción A — Recomendada (mediante el script del proyecto)

```bash
cd ~/apple-intelligence/apple-to-openai
uv run apple-to-openai
```

Esto inicia el servidor en `0.0.0.0:8000` por defecto.

**Bandera disponibles:**

| Bandera | Descripción | Valor predeterminado |
|---|---|---|
| `--host` | Dirección de enlace | `0.0.0.0` o `APPLE_AI_HOST` |
| `--port` | Número de puerto | Auto-detectado o `APPLE_AI_PORT` |
| `--reload` | Recargar automáticamente al cambiar el código (modo de desarrollo) | desactivado |
| `--strip-system-prompt` | Eliminar los mensajes del rol "system" | desactivado o `APPLE_AI_STRIP_SYSTEM_PROMPT` |
| `--custom-system-prompt` | Mensaje de sistema a inyectar cuando el stripping esté habilitado | `"Eres un asistente de programación útil."` |
| `--debug-payload` | Registrar el JSON de solicitud y respuesta en `./logs/` | desactivado o `APPLE_AI_DEBUG_PAYLOAD` |

Ejemplo:

```bash
uv run apple-to-openai --port 9000 --reload
```

### Opción B — Mediante `python -m`

```bash
uv run python __main__.py
# o
uv run python __main__.py --port 9000
```

### Opción C — Directamente con uvicorn (manual)

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## Configuración

Puedes configurar el servidor mediante variables de entorno. Se recomienda encarecidamente crear un archivo `.env` en la raíz del proyecto para fijar el puerto y otras configuraciones.

| Variable de entorno | Descripción | Valor predeterminado |
|---|---|---|
| `APPLE_AI_HOST` | Dirección de enlace | `0.0.0.0` |
| `APPLE_AI_PORT` | Número de puerto (si está vacío, detecta un puerto libre automáticamente) | `None` |
| `APPLE_AI_MAX_CONCURRENCY` | Máximo de solicitudes simultáneas al Modelo de Fundación | `4` |
| `APPLE_AI_REQUEST_TIMEOUT` | Tiempo de espera en segundos | `30.0` |
| `APPLE_AI_API_KEY` | Token de autenticación Bearer opcional | `None` |
| `APPLE_AI_STRIP_SYSTEM_PROMPT` | Establecer en `true` para eliminar los mensajes del sistema (útil para Opencode) | `False` |
| `APPLE_AI_CUSTOM_SYSTEM_PROMPT` | Mensaje de reemplazo inyectado cuando `STRIP_SYSTEM_PROMPT` es verdadero | `"Eres un asistente de programación útil."` |
| `APPLE_AI_DEBUG_PAYLOAD` | Establecer en `true` para registrar solicitudes/respuestas en `./logs/` | `False` |

**Nota de seguridad sobre `APPLE_AI_HOST`:**
Por defecto, el servidor se enlaza a `0.0.0.0`, lo que permite que otros dispositivos en tu red local (LAN) se conecten a tu Mac y utilicen tu Apple Intelligence. Si deseas restringir el acceso *solo a tu máquina local*, establece `APPLE_AI_HOST=127.0.0.1`.

**¿Por qué establecer un puerto fijo?**
Por defecto, el servidor escaneará un puerto disponible comenzando en `8000`. Si `8000` ya está en uso por otra aplicación, podría iniciarse en `8001`, `8002`, etc. Esto significa que necesitarías actualizar constantemente la URL en tus clientes de IA (Chatbox, OpenCode, etc.). Establecer un puerto fijo en `.env` evita esto.

**Ejemplo de archivo `.env`:**
```env
APPLE_AI_PORT=8002
APPLE_AI_MAX_CONCURRENCY=4
APPLE_AI_REQUEST_TIMEOUT=30.0
```

---

## Uso de la API

### Comprobación de estado

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Listar modelos

```bash
curl http://localhost:8000/v1/models
```

### Finalización de chat (streaming)

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "apple-intelligence",
    "messages": [{"role": "user", "content": "¿Qué es Apple Intelligence?"}],
    "stream": true
  }'
```

### Finalización de chat (no streaming)

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "apple-intelligence",
    "messages": [{"role": "user", "content": "¡Hola!"}],
    "stream": false
  }'
```

---

## Conectar clientes

Apunta cualquier cliente compatible con OpenAI a:

```
URL base: http://localhost:8000/v1
Clave API: cualquier-cadena-funciona (o tu APPLE_AI_API_KEY si está configurada)
Modelo: apple-intelligence
```

Ejemplos de clientes compatibles:

- [Open WebUI](https://github.com/open-webui/open-webui)
- [ChatBox](https://chatboxai.app/)
- [BoltAI](https://boltai.com/)
- Plugins de IDE (Continue, Cursor, alternativas de Copilot)
- Cualquier herramienta que use el SDK de OpenAI en Python/JS

### Configuración de OpenCode

Para conectar el Modelo de Fundación de Apple con OpenCode, añade lo siguiente a tu `opencode.jsonc` (en tu proyecto o en `~/.config/opencode/opencode.jsonc`):

> **Nota sobre `limit`**: El Modelo de Fundación de Apple tiene internamente un límite estricto de 4096 tokens. Proporcionar la opción `limit` a continuación indica a OpenCode que particione activamente el contexto antes de enviarlo a la API, evitando errores de "Límite de contexto excedido" en el extremo receptor.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "apple-fm-local": {
      "name": "Apple FM Local",
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://127.0.0.1:8000/v1"
      },
      "models": {
        "apple-intelligence": {
          "name": "Apple Intelligence",
          "tool_call": false,
          "limit": { "context": 4096, "output": 2048 }
        }
      }
    }
  },
  "model": "apple-fm-local/apple-intelligence"
}
```

Reinicia OpenCode y selecciona `apple-fm-local/apple-intelligence`.

### Rechazos y guardias de clientes (Importante)

El Modelo de Fundación de Apple tiene mecanismos de seguridad integrados para prevenir jailbreaks o sobrescrituras de instrucciones. Los plugins de IDE (como Opencode o Copilot) a menudo añaden mensajes de sistema masivos, de miles de palabras, llenos de instrucciones conductuales (por ejemplo, "Eres un programador experto... Debes responder en JSON...").

Cuando Apple Intelligence recibe estos masivos overrides de comportamiento, a menudo rechaza directamente el mensaje, resultando en respuestas como:
> *"Lo siento, pero no puedo cumplir con esa solicitud."*

**Solución:** Si tu editor recibe constantemente mensajes de rechazo, inicia el servidor utilizando la bandera `--strip-system-prompt` (o `APPLE_AI_STRIP_SYSTEM_PROMPT=true` en tu archivo `.env`). Esto elimina completamente el bloque de instrucciones oculto de `role="system"` antes de enviarlo al modelo de Apple.

Por defecto, el servidor inyecta un mensaje de reemplazo mínimo (`"Eres un asistente de programación útil."`) para mantener un contexto de seguridad sin activar los guardias. Puedes personalizar completamente este mensaje utilizando la bandera `--custom-system-prompt` (o la variable de entorno `APPLE_AI_CUSTOM_SYSTEM_PROMPT` en tu archivo `.env`).

Para investigar más a fondo lo que tu IDE está enviando, utiliza la bandera `--debug-payload` (o `APPLE_AI_DEBUG_PAYLOAD=true` en tu archivo `.env`). Esto escribirá cada solicitud y respuesta en bruto en un directorio `logs/` para que puedas inspeccionar los mensajes ocultos.

---

## Formato de streaming

El servidor sigue la especificación de streaming de OpenAI con dos mejoras adicionales de compatibilidad:

1. **Primer fragmento** envía el rol del asistente:
   ```json
   {"delta": {"role": "assistant"}}
   ```
2. **Antes del fragmento de finalización**, se envía un fragmento de contenido vacío:
   ```json
   {"delta": {"content": ""}}
   ```
3. **Fragmento de finalización** con `"finish_reason": "stop"`
4. **Señal `data: [DONE]`**

Esto garantiza la compatibilidad con clientes que esperan el anuncio del rol y/o una señal explícita de contenido vacío.

---

## Estructura del proyecto

```
apple-to-openai/
├── server.py          # Aplicación FastAPI y endpoints
├── __main__.py        # punto de entrada de python -m
├── pyproject.toml     # Metadatos del proyecto y dependencias
├── .gitignore         # Reglas de ignorar de git
└── README.md          # Este archivo
```

---

## Limitaciones

### Ventana de contexto

El Modelo de Fundación de Apple en el dispositivo tiene una ventana de contexto de **4,096 tokens** (entrada + salida combinados). El modelo estima el uso total de tokens antes de generar una respuesta; si la entrada combinada y la salida esperada exceden el límite, la solicitud es rechazada.

| Idioma | ~Longitud máxima de entrada | 1 token ≈ |
|---|---|---|
| **Inglés** | ~20,000 caracteres | 5 caracteres |
| **Chino** | ~6,400 caracteres (汉字) | 1.6 caracteres |
| **Mixto** | En algún punto intermedio | — |

En la práctica, esto significa:

- **Resumen / respuestas cortas**: La salida esperada es pequeña, por lo que la entrada puede ser bastante larga (cercana al máximo anterior).
- **Continuación de historias / ensayos largos**: El modelo anticipa una salida larga, dejando menos espacio para la entrada. Un prompt de 15,000 caracteres en inglés pidiendo un ensayo detallado puede ser rechazado, incluso aunque la misma longitud tendría éxito si solo se pidiera un resumen corto.

> **Nota:** Si se excede la ventana de contexto, el servidor devuelve un error `context_length_exceeded` compatible con OpenAI (HTTP 400) en lugar de bloquearse.

> **Nota:** Para conversaciones de varios turnos, el servidor trunca automáticamente los mensajes más antiguos para encajar dentro del límite de caracteres; mantiene el mensaje del sistema y los mensajes más recientes, descartando los más antiguos primero. Ver `truncate_messages()` en `server.py`.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `Modelo de Fundación no disponible` | Asegúrate de que Apple Intelligence esté habilitado y de que el modelo haya terminado de descargarse |
| La instalación de `apple_fm_sdk` falla | Asegúrate de que estás en macOS 26.0+ con Xcode 26.0+ instalado |
| `No se encontró solución` durante `uv sync` | Asegúrate de que `python-apple-fm-sdk` esté clonado como directorio hermano |
| Puerto ya en uso | Usa `--port <otro-puerto>` o mata el proceso existente |
| El streaming no funciona en el cliente | Verifica que el cliente soporte SSE; prueba el modo no streaming primero |

## Licencia

[Apache License 2.0](LICENSE)

*Si modificas o utilizas este proyecto, debes incluir el aviso de derechos de autor original y una copia de la licencia Apache 2.0. Esto garantiza la atribución a este repositorio original.*

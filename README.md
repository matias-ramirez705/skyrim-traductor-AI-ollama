<div align="center">

# 🐉 Skyrim Traductor AI — Ollama

### Agente de traducción de mods de Skyrim con IA local y terminología oficial

**Traduce mods del inglés al español latino usando RAG + Ollama + ChromaDB**

[![Python 3.11.9](https://img.shields.io/badge/Python-3.11.9-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3119/)
[![Ollama](https://img.shields.io/badge/Ollama-0.30.0+-000000?logo=ollama&logoColor=white)](https://ollama.com/)
[![Gradio](https://img.shields.io/badge/Gradio-6.x-FF7C00?logo=gradio&logoColor=white)](https://www.gradio.app/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.0+-4285F4?logo=google&logoColor=white)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📖 Tabla de Contenidos

- [🤔 ¿Qué hace este proyecto?](#-qué-hace-este-proyecto)
- [✨ Características](#-características)
- [🖥️ Interfaz del servidor de traducción](#-interfaz-del-servidor-de-traducción)
- [🧩 Interfaz del servidor del editor de JSON](#-interfaz-del-servidor-del-editor-de-json)
- [🖥️ Requisitos del Sistema](#️-requisitos-del-sistema)
- [📥 Descargas Necesarias](#-descargas-necesarias)
- [🚀 Instalación Paso a Paso](#-instalación-paso-a-paso)
- [📂 Estructura del Proyecto](#-estructura-del-proyecto)
- [🔧 Archivos BAT — Guía Completa](#-archivos-bat--guía-completa)
- [🐍 Archivos Python — Guía Completa](#-archivos-python--guía-completa)
- [⚙️ Configuración](#️-configuración)
- [🎯 Flujo de Trabajo](#-flujo-de-trabajo)
- [❓ Preguntas Frecuentes](#-preguntas-frecuentes)
- [🤝 Contribuir](#-contribuir)

---

## 🤔 ¿Qué hace este proyecto?

Este proyecto es un **agente de traducción automática** que traduce mods de Skyrim del **inglés al español latino**, respetando la terminología oficial del juego (nombres de lugares, NPCs, hechizos, facciones, etc.).

### ¿Cómo funciona?

```
Texto en inglés → Búsqueda de términos en ChromaDB (RAG) → Prompt con contexto → Ollama traduce → Texto en español
```

1. 📥 Pegas el texto en inglés desde **ESP Translate**
2. 🔍 El sistema busca **términos oficiales** en la base de datos vectorial (27,955 términos)
3. 🧠 Construye un **prompt con contexto** de traducciones obligatorias
4. 🤖 **Ollama** (modelo Qwen2.5 7B) traduce respetando la terminología
5. 📤 Copias el resultado y lo pegas de vuelta en ESP Translate

> **Todo funciona 100% en local** — no necesitas internet ni API keys. Tu PC es el servidor.

---

## ✨ Características

- 🏠 **100% local** — Sin APIs externas, sin costos, sin límites
- 📚 **27,955 términos** del juego original (Skyrim + DLCs) en la base de datos
- 🧠 **RAG (Retrieval-Augmented Generation)** — Busca terminología relevante antes de traducir
- 🎯 **3 prompts predefinidos** — Traducción general, Diálogo Khajiit, Libros y Notas
- ✏️ **Editor de prompts** — Crea, edita y gestiona prompts personalizados
- 📝 **Editor de glosario** — Agrega, modifica y elimina términos del glosario
- 🎨 **Interfaz web** con Gradio — Tema configurable y contadores de líneas
- 🔧 **Configuración visual** — Personaliza colores, fuentes y layout desde JSON
- 📋 **Flujo integrado con ESP Translate** — Copiar y pegar directo

---
## 🖥️ Interfaz del servidor de traducción

<p align="center">
  <img src="Imagenes/interfaz traductor 1.png" width="45%">
  <img src="Imagenes/interfaz traductor 2.png" width="45%">
</p>

<p align="center">
  <img src="Imagenes/interfaz traductor 3.png" width="60%">
</p>

---

## 🧩 Interfaz del servidor del editor de JSON

<p align="center">
  <img src="Imagenes/editor glosario 1.png" width="45%">
  <img src="Imagenes/editor glosario 2.png" width="45%">
</p>

<p align="center">
  <img src="Imagenes/editor glosario 3.png" width="45%">
  <img src="Imagenes/editor glosario 4.png" width="45%">
</p>

<p align="center">
  <img src="Imagenes/editor glosario 5.png" width="60%">
</p>

---
## 🖥️ Requisitos del Sistema

### Mínimos

| Componente | Requisito | Nota |
|---|---|---|
| 🎮 **GPU** | NVIDIA con 6 GB VRAM | Para ejecutar Qwen2.5 7B en Q4 |
| 💾 **RAM** | 16 GB | El modelo usa ~5 GB en memoria |
| 💽 **Disco** | 10 GB libres | Modelo + ChromaDB + dependencias |
| 🖥️ **CPU** | 4 núcleos | Para inference del modelo |
| 🪟 **SO** | Windows 10/11 64-bit | Los `.bat` son para Windows |

### Recomendados (testeado en este hardware ✅)

| Componente | Especificación | Rendimiento |
|---|---|---|
| 🎮 **GPU** | **RTX 4060 8 GB VRAM** | Traducción rápida (~3-5 seg por párrafo) |
| 💾 **RAM** | **32 GB DDR5** | Sobrado para el modelo + ChromaDB |
| 🖥️ **CPU** | **i5-14400F** | Excelente para inference + búsqueda vectorial |
| 💽 **Disco** | SSD | Inicio rápido del servidor y ChromaDB |

> 💡 **Nota sobre GPU**: El modelo Qwen2.5 7B cuantizado (Q4) usa aproximadamente **4.5 GB de VRAM**. Con una RTX 4060 de 8 GB tienes espacio de sobra. Si tienes menos VRAM, puedes usar `qwen2.5:1.5b` o `qwen2.5:3b` cambiando la constante `OLLAMA_MODEL` en el código.

---

## 📥 Descargas Necesarias

### 1. 🐍 Python 3.11.9

> ⚠️ **Importante**: Usar **exactamente** Python 3.11.9. Versiones más nuevas pueden tener incompatibilidades con ChromaDB y otras dependencias.

🔗 **Descargar**: [Python 3.11.9 para Windows (64-bit)](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)

📌 Durante la instalación:
- ✅ Marca **"Add Python 3.11 to PATH"**
- ✅ Selecciona **"Install Now"**

### 2. 🦙 Ollama

Ollama es el motor que ejecuta el modelo de IA en tu GPU local.

🔗 **Descargar**: [Ollama para Windows](https://ollama.com/download/windows)

📌 Durante la instalación:
- ✅ Sigue el instalador normal
- ✅ Ollama se instala en `%LOCALAPPDATA%\Programs\Ollama\`
- ✅ Después de instalar, abre Ollama desde el Menú Inicio

### 3. 🧠 Modelo Qwen2.5 7B

El modelo se descarga **automáticamente** la primera vez que ejecutas `4_iniciar_servidor.bat` (tarda 10-20 minutos). Pero si quieres descargarlo antes:

```bash
ollama pull qwen2.5:7b
```

Modelos alternativos (más livianos):

| Modelo | VRAM requerida | Calidad | Comando |
|---|---|---|---|
| `qwen2.5:7b` | ~4.5 GB | ⭐⭐⭐⭐⭐ Mejor calidad | `ollama pull qwen2.5:7b` |
| `qwen2.5:3b` | ~2 GB | ⭐⭐⭐ Buena | `ollama pull qwen2.5:3b` |
| `qwen2.5:1.5b` | ~1 GB | ⭐⭐ Aceptable | `ollama pull qwen2.5:1.5b` |

### 4. 🔧 Git (opcional — para clonar el repo)

🔗 **Descargar**: [Git para Windows](https://git-scm.com/download/win)

---

## 🚀 Instalación Paso a Paso

### Clonar el repositorio

```bash
git clone https://github.com/Krou705/skyrim-traductor-AI-ollama.git
```

> 💡 También puedes descargar el ZIP desde GitHub y descomprimirlo donde quieras.

### Crear el entorno virtual

Abre una terminal (CMD) en la carpeta del proyecto y ejecuta:

```bash
python -m venv venv
```

Esto crea la carpeta `venv\` con el entorno virtual de Python.

### Orden de ejecución

Sigue estos pasos **en orden**. Solo necesitas hacerlos **una vez** la primera vez:

| Paso | Archivo | Qué hace | ¿Cuándo ejecutarlo? |
|---|---|---|---|
| 1️⃣ | `2_instalar_dependencias.bat` | Instala chromadb, ollama, gradio | **Solo la primera vez** |
| 2️⃣ | `3_iniciar_glosario.bat` | Carga el glosario en ChromaDB | **Solo la primera vez** o cuando cambies el glosario |
| 3️⃣ | `4_iniciar_servidor.bat` | Inicia el servidor de traducción | **Cada vez que quieras traducir** |

> ✅ **El glosario ya está generado** — El archivo `skyrim_glossary_en_es.json` ya viene incluido en el repositorio con 27,955 términos. **NO necesitas ejecutar** `1_crear_glosario.bat` a menos que quieras regenerarlo desde los archivos `.strings` originales.

### Detalle de cada paso

#### 1️⃣ Instalar dependencias

```bash
2_instalar_dependencias.bat
```

Esto instala dentro del venv:
- `chromadb` — Base de datos vectorial para búsqueda semántica
- `ollama` — Cliente Python para comunicarse con Ollama
- `gradio` — Interfaz web del traductor

⏱️ Tarda ~3-5 minutos la primera vez.

#### 2️⃣ Cargar glosario en ChromaDB

```bash
3_iniciar_glosario.bat
```

Esto lee `skyrim_glossary_en_es.json` y lo carga en ChromaDB (búsqueda vectorial). Crea la carpeta `BD\chroma_db\`.

⏱️ Tarda ~1-2 minutos.

#### 3️⃣ Iniciar el servidor de traducción

```bash
4_iniciar_servidor.bat
```

Esto:
1. ✅ Verifica que Ollama esté corriendo (lo inicia si no está)
2. ✅ Verifica que el modelo `qwen2.5:7b` esté disponible (lo descarga si falta)
3. ✅ Inicia la interfaz web en **http://localhost:7860**
4. ✅ Abre automáticamente tu navegador

🌐 La interfaz web se abre en tu navegador. Para detener el servidor, cierra la ventana del CMD o presiona `Ctrl+C`.

---

## 📂 Estructura del Proyecto

```
skyrim-traductor-AI-ollama/
├── 📄 README.md                          ← Estás aquí
├── 📄 requirements.txt                   ← Dependencias Python
│
├── 🦇 Archivos BAT (ejecutables)
│   ├── 0_abrir_cmd_venv.bat              ← CMD con venv activado
│   ├── 1_crear_glosario.bat              ← Genera JSON desde .strings
│   ├── 2_instalar_dependencias.bat       ← Instala paquetes Python
│   ├── 3_iniciar_glosario.bat            ← Carga JSON en ChromaDB
│   ├── 4_iniciar_servidor.bat            ← Inicia servidor traducción
│   ├── 5_actualizar_glosario.bat         ← Agrega términos nuevos
│   ├── 6_iniciar_editor_glosario.bat     ← Editor web de glosario
│   └── 7_limpiar_glosario.bat            ← Limpia entradas corruptas
│
├── 🐍 Codigo_py/                         ← Código fuente Python
│   ├── 0_crear_glosario.py               ← Parser de .strings → JSON
│   ├── crear_glosario.py                 ← Alias del anterior
│   ├── 1_cargar_glosario.py              ← JSON → ChromaDB
│   ├── 2_servidor_traduccion.py          ← Servidor Gradio + RAG
│   ├── 5_editor_glosario.py              ← Editor web de glosario
│   ├── actualizar_glosario.py            ← Agrega términos nuevos
│   └── limpiar_glosario.py              ← Limpia JSON corrupto
│
├── ⚙️ servidor_config/                   ← Configuración
│   ├── config_visual.json                ← Tema, colores, fuentes
│   ├── strings_ui.json                   ← Textos de la interfaz
│   └── prompts/
│       └── saved_prompts.json            ← Prompts guardados (se crea al usar)
│
├── 📚 BD/                                ← Base de datos y glosario
│   ├── skyrim_glossary_en_es.json        ← Glosario 27,955 términos ✅
│   ├── palabras_agregadas.json           ← Términos manuales (opcional)
│   ├── chroma_db/                        ← Base vectorial ChromaDB
│   ├── 0 - English Original Strings/     ← Archivos .strings EN (opcional)
│   └── 0 - Spanish Original Strings/     ← Archivos .strings ES (opcional)
│
├── 🔧 venv/                              ← Entorno virtual Python
│
└── 🔄 Git (opcional)
    ├── git_subir_primera_vez.bat         ← Primera subida a GitHub
    ├── git_subir_cambios.bat             ← Subir cambios
    └── git_descargar_cambios.bat         ← Descargar cambios
```

---

## 🔧 Archivos BAT — Guía Completa

### `0_abrir_cmd_venv.bat` — 🔧 Utilidad

Abre una ventana de CMD con el entorno virtual ya activado. Útil para ejecutar comandos Python manualmente o debuguear.

```bash
0_abrir_cmd_venv.bat
```

---

### `1_crear_glosario.bat` — 📚 Generar glosario (OPCIONAL)

> ⚠️ **No necesitas ejecutar esto** — El glosario `skyrim_glossary_en_es.json` ya viene incluido en el repo.

Genera el archivo JSON del glosario a partir de los archivos `.strings` binarios de Skyrim. Solo lo necesitas si:
- Quieres regenerar el glosario desde cero
- Tienes archivos `.strings` de otros mods o DLCs que quieres agregar

**Requisito**: Los archivos `.strings` deben estar en:
- `BD/0 - English Original Strings/strings/`
- `BD/0 - Spanish Original Strings/strings/`

```bash
1_crear_glosario.bat
```

⏱️ Tarda ~5-10 minutos dependiendo de la cantidad de archivos.

---

### `2_instalar_dependencias.bat` — 📦 Instalar (PRIMERA VEZ)

Instala las dependencias de Python dentro del entorno virtual:

| Paquete | Versión | Para qué sirve |
|---|---|---|
| `chromadb` | >= 1.0.0 | Base de datos vectorial para búsqueda semántica |
| `ollama` | >= 0.4.0 | Cliente para comunicarse con Ollama |
| `gradio` | >= 5.0, < 7.0 | Interfaz web del traductor |

```bash
2_instalar_dependencias.bat
```

⏱️ Tarda ~3-5 minutos la primera vez.

---

### `3_iniciar_glosario.bat` — 🗄️ Cargar glosario (PRIMERA VEZ)

Lee `skyrim_glossary_en_es.json` y lo carga en ChromaDB para búsqueda semántica. Crea la carpeta `BD/chroma_db/`.

```bash
3_iniciar_glosario.bat
```

⏱️ Tarda ~1-2 minutos. Solo ejecútalo la primera vez o cuando cambies el glosario.

---

### `4_iniciar_servidor.bat` — 🚀 Iniciar traductor (USO DIARIO)

El archivo principal. Inicia el servidor de traducción con interfaz web Gradio.

**Qué hace automáticamente:**
1. 🦙 Verifica que Ollama esté corriendo → Lo inicia si no está
2. 🧠 Verifica que `qwen2.5:7b` esté disponible → Lo descarga si falta
3. 🌐 Inicia el servidor en `http://localhost:7860`
4. 🖥️ Abre tu navegador automáticamente

```bash
4_iniciar_servidor.bat
```

> 💡 Para detener: cierra la ventana del CMD o presiona `Ctrl+C`

---

### `5_actualizar_glosario.bat` — ➕ Agregar términos

Agrega términos nuevos a ChromaDB sin necesidad de recargar todo el glosario. Lee términos de:
- `BD/palabras_agregadas.json` (términos manuales)
- Cualquier otro JSON en `BD/` (excepto el glosario principal)

```bash
5_actualizar_glosario.bat
```

Úsalo cuando agregues términos manualmente al glosario y quieras que el traductor los encuentre.

---

### `6_iniciar_editor_glosario.bat` — ✏️ Editor de glosario

Inicia una interfaz web para editar el glosario directamente desde el navegador.

```bash
6_iniciar_editor_glosario.bat
```

🌐 Se abre en **http://localhost:7861** (puerto diferente al traductor)

**Funciones del editor:**
- ➕ Agregar términos (individual o en lote)
- 🔍 Buscar y editar términos existentes
- 📂 Ver archivos en la carpeta BD/
- 🏷️ 18 categorías con colores (lugar, npc, magia, arma, etc.)
- 📋 7 tipos (nombre, verbo, adjetivo, frase, diálogo, descripción, otro)

> 💡 Puedes tener el traductor y el editor abiertos al mismo tiempo en puertos diferentes.

---

### `7_limpiar_glosario.bat` — 🧹 Limpiar glosario

Elimina entradas corruptas o vacías del archivo JSON del glosario. Crea un backup automáticamente antes de limpiar.

```bash
7_limpiar_glosario.bat
```

**Qué elimina:**
- Entradas con texto español vacío
- Entradas con inglés de 1 carácter o menos
- Entradas duplicadas

**Backup**: Crea `skyrim_glossary_en_es_backup.json` antes de modificar.

---

### 🔄 Archivos Git (opcionales)

| Archivo | Qué hace |
|---|---|
| `git_subir_primera_vez.bat` | Guía paso a paso para subir el repo a GitHub por primera vez |
| `git_subir_cambios.bat` | Sube cambios locales a GitHub (`git add + commit + push`) |
| `git_descargar_cambios.bat` | Descarga cambios desde GitHub (`git pull`) |

---

## 🐍 Archivos Python — Guía Completa

### `0_crear_glosario.py` — Parser de archivos .strings

**Ubicación**: `Codigo_py/0_crear_glosario.py` | **Ejecutado por**: `1_crear_glosario.bat`

Parsea los archivos binarios `.strings`, `.dlstrings` e `.ilstrings` del formato Bethesda y genera `skyrim_glossary_en_es.json`.

**Características:**
- 🔢 Parser binario del formato Bethesda (header + directory + data block)
- 🏷️ Clasificación automática por categoría (lugar, npc, magia, arma, armadura, criatura, facción, misión, diálogo, descripción)
- 🔗 Emparejamiento de entradas EN/ES por stringID
- 🧹 Limpieza y deduplicación de entradas
- 📂 Escaneo automático de todos los archivos `.strings` en las carpetas de BD

---

### `1_cargar_glosario.py` — Cargador de ChromaDB

**Ubicación**: `Codigo_py/1_cargar_glosario.py` | **Ejecutado por**: `3_iniciar_glosario.bat`

Lee el JSON del glosario y lo carga en una base de datos vectorial ChromaDB persistente.

**Características:**
- 📦 Inserción por lotes (5000 por batch)
- 📝 Documentos almacenados como `"english | spanish"` para búsqueda bilingüe
- 💾 Almacenamiento persistente en `BD/chroma_db/`
- 🧪 Búsquedas de prueba (Whiterun, Stormcloaks, dragon shout, etc.)

---

### `2_servidor_traduccion.py` — Servidor de traducción ⭐

**Ubicación**: `Codigo_py/2_servidor_traduccion.py` | **Ejecutado por**: `4_iniciar_servidor.bat`

El corazón del proyecto. Interfaz web Gradio + motor RAG + Ollama.

**Componentes principales:**

| Componente | Descripción |
|---|---|
| 🔍 **Motor RAG** | Busca términos relevantes en ChromaDB y construye contexto |
| 🤖 **Traductor** | Envía prompt + contexto a Ollama para traducir |
| 📝 **PromptManager** | CRUD de prompts personalizados |
| 🎨 **Config visual** | Carga tema, colores y textos desde JSON |
| 🖥️ **Interfaz Gradio** | Dos tabs: Traducir y Mis Prompts |

**Configuración del motor:**
- **Modelo**: `qwen2.5:7b`
- **Temperatura**: 0.1 (baja para traducción consistente)
- **Búsqueda ChromaDB**: 80 resultados iniciales → filtrado a 30 mejores
- **Puerto**: 7860

**Prompts predefinidos:**
1. 🎮 **Traducción Skyrim (por defecto)** — 12 reglas obligatorias con lista de no-traducir
2. 🐱 **Diálogo Khajiit** — Mantiene habla en tercera persona
3. 📖 **Libros y Notas** — Tono literario y narrativo medieval

---

### `5_editor_glosario.py` — Editor de glosario web

**Ubicación**: `Codigo_py/5_editor_glosario.py` | **Ejecutado por**: `6_iniciar_editor_glosario.bat`

Interfaz web para editar el glosario JSON desde el navegador.

**4 tabs:**
- ➕ **Agregar líneas** — Individual o en lote
- 👁️ **Vista previa** — Con syntax highlighting
- 🔍 **Buscar y editar** — Búsqueda y edición de términos
- 📂 **Archivos en BD** — Ver archivos de la carpeta BD

**Categorías con colores:**

| Categoría | Color | Categoría | Color |
|---|---|---|---|
| 🏰 Lugar | 🟢 Verde | 🗡️ Arma | 🔵 Azul |
| 👤 NPC | 🟠 Naranja | 🛡️ Armadura | 🟣 Púrpura |
| ✨ Magia | 🔴 Rojo | 🐉 Criatura | 🟤 Marrón |
| ⚔️ Facción | 🟡 Amarillo | 📜 Misión | 🔵 Cian |

---

### `actualizar_glosario.py` — Actualizador de términos

**Ubicación**: `Codigo_py/actualizar_glosario.py` | **Ejecutado por**: `5_actualizar_glosario.bat`

Agrega términos nuevos a ChromaDB sin recargar todo. Deduplica contra entradas existentes.

---

### `limpiar_glosario.py` — Limpiador de JSON

**Ubicación**: `Codigo_py/limpiar_glosario.py` | **Ejecutado por**: `7_limpiar_glosario.bat`

Elimina entradas corruptas del JSON. Crea backup automático. Verifica que términos clave sigan existiendo después de la limpieza.

---

## ⚙️ Configuración

### 🎨 Configuración visual — `servidor_config/config_visual.json`

Personaliza la apariencia de la interfaz web:

```json
{
  "tema": "Soft",
  "color_primario": "blue",
  "colores_personalizados": {
    "fondo_titulo": "#1a1a2e",
    "texto_titulo": "#e0e0e0"
  },
  "fuentes": {
    "titulo": "Segoe UI, sans-serif",
    "tamano_titulo": "28px"
  },
  "layout": {
    "altura_texto_entrada": 12,
    "mostrar_lineas": true
  }
}
```

### 📝 Textos de la interfaz — `servidor_config/strings_ui.json`

Todos los textos, labels, tooltips y mensajes de la interfaz son configurables. 60+ claves en español.

### 💬 Prompts guardados — `servidor_config/prompts/saved_prompts.json`

Los prompts personalizados se guardan automáticamente aquí. Se crea la primera vez que usas el editor de prompts.

---

## 🎯 Flujo de Trabajo

### Flujo diario (traducir mods)

```
1. Abre Ollama desde el Menú Inicio
2. Ejecuta 4_iniciar_servidor.bat
3. Se abre http://localhost:7860 en tu navegador
4. En ESP Translate, copia las líneas en inglés
5. Pégalas en el panel izquierdo del traductor
6. Selecciona el prompt deseado (general, Khajiit, libros)
7. Presiona "Traducir"
8. Copia el resultado del panel derecho
9. Pégalo de vuelta en ESP Translate
```

### Flujo completo (primera vez)

```
1. Instala Python 3.11.9
2. Instala Ollama
3. Clona el repo
4. Ejecuta: python -m venv venv
5. Ejecuta: 2_instalar_dependencias.bat
6. Ejecuta: 3_iniciar_glosario.bat
7. Ejecuta: 4_iniciar_servidor.bat
8. ¡Listo! 🎉
```

### Diagrama de datos

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Archivos       │     │  JSON del        │     │  ChromaDB       │
│  .strings       │────▶│  Glosario        │────▶│  (Vector DB)    │
│  (binarios)     │     │  27,955 términos │     │  Búsqueda RAG   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Texto en       │────▶│  Motor RAG       │────▶│  Prompt +       │
│  inglés         │     │  Busca términos  │     │  Contexto       │
│  (de ESP        │     │  relevantes      │     │                 │
│   Translate)    │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │  Ollama         │
                                                │  Qwen2.5 7B     │
                                                │  Traduce        │
                                                └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │  Texto en       │
                                                │  español        │
                                                │  (para ESP      │
                                                │   Translate)    │
                                                └─────────────────┘
```

---

## ❓ Preguntas Frecuentes

### 🐌 ¿Es lenta la traducción?

Con una RTX 4060, cada traducción tarda ~3-5 segundos por párrafo. Si usas CPU sola puede tardar 30-60 segundos. La primera traducción siempre es más lenta (el modelo se está cargando en VRAM).

### 🔄 ¿Puedo usar otro modelo?

Sí. Edita `OLLAMA_MODEL` en `Codigo_py/2_servidor_traduccion.py`:

```python
OLLAMA_MODEL = "qwen2.5:3b"   # Más rápido, menos calidad
OLLAMA_MODEL = "qwen2.5:14b"  # Más calidad, necesita más VRAM
```

### 📝 ¿Puedo agregar términos al glosario?

Sí, hay 3 formas:
1. **Editor web**: Ejecuta `6_iniciar_editor_glosario.bat` → Abre en `localhost:7861`
2. **Archivo JSON**: Agrega términos a `BD/palabras_agregadas.json` y ejecuta `5_actualizar_glosario.bat`
3. **Regenerar**: Si tienes archivos `.strings` nuevos, ejecuta `1_crear_glosario.bat`

### 🎨 ¿Puedo cambiar el tema de la interfaz?

Sí. Edita `servidor_config/config_visual.json`:

```json
{
  "tema": "Glass",
  "color_primario": "green"
}
```

Reinicia el servidor para ver los cambios.

### 🌐 ¿Necesito internet?

Solo para:
- Descargar Ollama y el modelo (una vez)
- Instalar dependencias de Python (una vez)

**Después de eso, todo funciona 100% offline.** 🏠

### ⚠️ ¿Qué hago si Ollama no arranca?

1. Abre Ollama manualmente desde el Menú Inicio
2. Espera a que aparezca el ícono en la bandeja del sistema
3. Ejecuta `4_iniciar_servidor.bat` de nuevo

### 💾 ¿Cuánto espacio usa?

| Componente | Espacio |
|---|---|
| Modelo Qwen2.5 7B | ~4.7 GB |
| ChromaDB | ~500 MB |
| Dependencias Python | ~1.5 GB |
| Glosario JSON | ~15 MB |
| **Total** | **~7 GB** |

### 🔀 ¿Puedo tener el traductor y el editor abiertos a la vez?

¡Sí! El traductor usa el puerto **7860** y el editor el puerto **7861**. No hay conflicto.

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Puedes:

1. 🍴 Hacer fork del repositorio
2. 🌿 Crear una rama (`git checkout -b feature/nueva-funcion`)
3. 💾 Hacer commit de tus cambios (`git commit -m "Agrega nueva función"`)
4. 📤 Hacer push a la rama (`git push origin feature/nueva-funcion`)
5. 🔄 Abrir un Pull Request

O simplemente reportar bugs o sugerir mejoras en los **Issues** del repositorio.

---

<div align="center">

### 🐉 Hecho con ❤️ para la comunidad de traductores de mods de Skyrim

**Motor**: Ollama + ChromaDB + RAG | **Modelo**: Qwen2.5 7B | **Interfaz**: Gradio

</div>

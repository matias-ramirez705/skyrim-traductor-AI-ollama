"""
=====================================================
PASO 4-5: Servidor de Traduccion con Interfaz Grafica
=====================================================
Interfaz web Gradio + RAG (ChromaDB) + Ollama

Compatible con:
  - Python 3.11.9
  - Ollama 0.30.0 (servidor)
  - ollama Python >= 0.4.0 (libreria)
  - Gradio >= 6.0
  - chromadb >= 1.0

Flujo: Texto ingles -> Busqueda de terminos en ChromaDB
       -> Prompt con contexto -> Ollama traduce -> Texto espanol

USO: python 2_servidor_traduccion.py
Luego abre en el navegador: http://localhost:7860
"""

import os
import sys
import json
import traceback
import re
import time

import gradio as gr
import ollama

# ============================================================
# CONFIGURACION
# ============================================================
from pathlib import Path

# Detectar carpeta base del proyecto
SCRIPT_DIR = Path(__file__).resolve().parent

possible_paths = [
    SCRIPT_DIR,
    SCRIPT_DIR.parent
]

BASE_DIR = SCRIPT_DIR

for path in possible_paths:
    if (path / "BD").exists():
        BASE_DIR = path
        break

# Rutas derivadas
CHROMA_DIR = BASE_DIR / "BD" / "chroma_db"
COLLECTION_NAME = "skyrim_terminology"

PROMPTS_DIR = BASE_DIR / "servidor_config" / "prompts"
CONFIG_FILE = BASE_DIR / "servidor_config" / "config_visual.json"
STRINGS_FILE = BASE_DIR / "servidor_config" / "strings_ui.json"

OLLAMA_MODEL = "qwen2.5:7b"
CHROMA_SEARCH_LIMIT = 80
MAX_CONTEXT_TERMS = 30
TEMPERATURE = 0.1
GRADIO_PORT = 7860

# --- NUEVO: Tamaño de fragmento para traduccion por lotes ---
# Cuando el texto tiene mas lineas que este valor, se divide en fragmentos
# y cada uno se traduce por separado con el mismo contexto del glosario.
# Menos lineas = mejor calidad (el modelo sigue el glosario), mas lento.
# Mas lineas = mas rapido, pero puede perder terminologia.
DEFAULT_CHUNK_SIZE = 8  # Lineas por fragmento al traducir textos largos


# ============================================================
# CARGAR CONFIGURACION VISUAL Y STRINGS
# ============================================================
def load_json_config(filepath, fallback=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[AVISO] Error cargando {filepath}: {e}")
    return fallback or {}


DEFAULT_STRINGS = {
    "titulo": "Agente de Traducci\u00f3n Skyrim",
    "subtitulo": "Traductor con contexto del juego usando IA local + terminolog\u00eda oficial",
    "tab_traducir": "Traducir",
    "tab_prompts": "Mis Prompts",
    "panel_entrada_titulo": "Texto en Ingl\u00e9s",
    "panel_entrada_descripcion": "Pega aqu\u00ed las l\u00edneas desde ESP Translate",
    "panel_entrada_label": "Texto Original (Ingl\u00e9s)",
    "panel_entrada_placeholder": "Pega aqu\u00ed las l\u00edneas a traducir...\n\nEjemplo:\nWhiterun is a city in the hold of Whiterun.\nThe Stormcloaks are fighting the Imperial Legion.",
    "panel_salida_titulo": "Traducci\u00f3n al Espa\u00f1ol",
    "panel_salida_descripcion": "Copia este texto y p\u00e9galo en ESP Translate",
    "panel_salida_label": "Texto Traducido (Espa\u00f1ol)",
    "panel_salida_placeholder": "La traducci\u00f3n aparecer\u00e1 aqu\u00ed...",
    "slider_terminos_label": "T\u00e9rminos de contexto",
    "slider_terminos_tooltip": "Controla cu\u00e1ntos t\u00e9rminos de Skyrim se buscan en la base de datos para dar contexto a la IA. M\u00e1s t\u00e9rminos = mejor precisi\u00f3n en nombres, pero traducci\u00f3n m\u00e1s lenta. Recomendado: 30 para textos normales, 50 para textos con muchos nombres propios.",
    "selector_prompt_label": "Prompt de traducci\u00f3n",
    "selector_prompt_refrescar": "Actualizar",
    "descripcion_prompt_label": "Descripci\u00f3n del prompt",
    "btn_traducir": "Traducir",
    "btn_limpiar": "Limpiar",
    "accordion_terminos_titulo": "T\u00e9rminos encontrados",
    "accordion_terminos_label": "T\u00e9rminos relevantes",
    "accordion_contexto_titulo": "Contexto enviado al modelo",
    "accordion_contexto_label": "Contexto RAG completo",
    "footer_flujo": "Flujo: ESP Translate \u2192 Copiar \u2192 Pegar aqu\u00ed \u2192 Traducir \u2192 Copiar resultado \u2192 Pegar en ESP Translate",
    "prompts_seccion_descripcion": "**Gestiona tus prompts de traducci\u00f3n.** Crea prompts personalizados para diferentes tipos de texto (di\u00e1logos, libros, personajes espec\u00edficos, etc.). Los prompts se guardan autom\u00e1ticamente en `servidor_config/prompts/saved_prompts.json`.",
    "prompts_lista_label": "Selecciona un prompt",
    "prompts_lista_titulo": "Prompts guardados",
    "prompts_cargar_btn": "Cargar para editar",
    "prompts_duplicar_btn": "Duplicar",
    "prompts_eliminar_btn": "Eliminar",
    "prompts_nuevo_btn": "Nuevo prompt",
    "prompts_editor_titulo": "Editor de prompt",
    "prompts_nombre_label": "Nombre del prompt",
    "prompts_nombre_placeholder": "Ej: Di\u00e1logo Argoniano",
    "prompts_desc_label": "Descripci\u00f3n (para qu\u00e9 sirve)",
    "prompts_desc_placeholder": "Ej: Traducci\u00f3n especial para di\u00e1logos de personajes Argonianos",
    "prompts_contenido_label": "Contenido del prompt (system prompt)",
    "prompts_contenido_placeholder": "Escribe aqu\u00ed las instrucciones que recibir\u00e1 la IA...",
    "prompts_guardar_btn": "Guardar prompt",
    "prompts_probar_btn": "Ir a Traducir para probar",
    "prompts_estado_label": "Estado",
    "lineas_info_prefix": "L\u00edneas: ",
    "caracteres_info_prefix": "Caracteres: ",
    "traduccion_sin_texto": "No se ingres\u00f3 texto.",
    "prompt_no_encontrado": "Prompt no encontrado",
    "prompt_nombre_vacio": "Escribe un nombre para el prompt",
    "prompt_contenido_vacio": "El contenido del prompt no puede estar vac\u00edo",
    "prompt_creado": "creado",
    "prompt_actualizado": "actualizado",
    "prompt_eliminado": "eliminado",
    "prompt_no_default": "No se puede eliminar el prompt por defecto",
    "prompt_selecciona": "Selecciona un prompt para eliminar",
    "prompt_nuevo_msg": "Escribe el nombre, descripci\u00f3n y contenido del nuevo prompt"
}

DEFAULT_CONFIG = {
    "titulo_pagina": "Agente de Traduccion Skyrim",
    "tema": "Soft",
    "color_primario": "blue",
    "colores_personalizados": {"fondo_titulo": "#1a1a2e", "texto_titulo": "#e0e0e0"},
    "fuentes": {"titulo": "Segoe UI, sans-serif", "tamano_titulo": "28px", "tamano_subtitulo": "14px"},
    "layout": {"centrar_titulo": True, "centrar_botones": True, "altura_texto_entrada": 12, "altura_texto_salida": 12, "mostrar_lineas": True}
}

config = {**DEFAULT_CONFIG, **load_json_config(CONFIG_FILE, {})}
S = {**DEFAULT_STRINGS, **load_json_config(STRINGS_FILE, {})}


# ============================================================
# GESTOR DE PROMPTS
# ============================================================
DEFAULT_PROMPT = {
    "name": "Traduccion Skyrim (por defecto)",
    "description": "Prompt est\u00e1ndar para traducir mods de Skyrim del ingl\u00e9s al espa\u00f1ol latino con terminolog\u00eda oficial.",
    "content": """Eres un traductor experto de mods de Skyrim del ingles al espanol latino.

REGLAS OBLIGATORIAS:
1. Traduce TODO el texto al espanol. NO dejes palabras en ingles sin traducir.
2. Usa EXCLUSIVAMENTE la terminologia oficial de Skyrim que aparece en la seccion "TRADUCCIONES OBLIGATORIAS" del CONTEXTO.
3. Si un nombre aparece en TRADUCCIONES OBLIGATORIAS, usa ESA traduccion EXACTA, sin excepcion.
4. Si un nombre aparece en TRADUCCIONES OBLIGATORIAS como no traducido (ej: "Jorrvaskr -> Jorrvaskr"), dejalo tal cual.
5. Nombres que NO se traducen NUNCA: Thu'um, Thalmor, Daedra, Draugr, Nirn, Aedra, Alduin, Paarthurnax, Mehrunes Dagon, Hermaeus Mora, Hircine, Molag Bal, Namira, Nocturnal, Sanguine, Sheogorath, Vaermina, Clavicus Vile, Meridia, Azura, Boethiah, Mephala, Malacath, Peryite, Jyggalag, Kematu, Alik'r.
6. Mantiene EXACTAMENTE la estructura: mismas lineas, orden y saltos de linea.
7. Mantiene las etiquetas HTML/ESP intactas (ej: <Alias=Player>, <Global=...>, <Alias.Race>).
8. Mantiene los separadores de linea exactamente como estan.
9. Mantiene las llaves {} y su contenido intactas cuando contengan etiquetas como <Global=...>.
10. Para terminos que NO aparecen en el CONTEXTO, traduce de la forma mas natural al espanol latino manteniendo el tono de fantasia medieval de Skyrim.
11. NO agregues notas, explicaciones ni comentarios. Solo la traduccion.
12. Se CONSISTENTE: si traduciste "Whiterun" como "Carrera Blanca" en una linea, traducelo igual en TODAS las lineas.

FORMATO DE SALIDA:
- Devuelve SOLO las lineas traducidas, en el mismo orden y cantidad que el original.
- Cada linea traducida corresponde a una linea del original.
- Si el original tiene N lineas, la traduccion debe tener exactamente N lineas.
- NO mezcles ingles y espanol en la misma linea.""",
    "is_default": True
}

EXTRA_PROMPTS = [
    {
        "name": "Di\u00e1logo Khajiit",
        "description": "Traducci\u00f3n de di\u00e1logos de personajes Khajiit, manteniendo su estilo de habla en tercera persona.",
        "content": """Eres un traductor experto de mods de Skyrim del ingles al espanol latino, especializado en dialogos de personajes Khajiit.

REGLAS OBLIGATORIAS:
1. Traduce TODO el texto al espanol. NO dejes palabras en ingles sin traducir.
2. Los Khajiit hablan en tercera persona (ej: "This one thinks..." -> "Este piensa..."). Manten ese estilo.
3. Usa EXCLUSIVAMENTE la terminologia oficial de Skyrim que aparece en "TRADUCCIONES OBLIGATORIAS".
4. Si un nombre aparece en TRADUCCIONES OBLIGATORIAS, usa ESA traduccion EXACTA.
5. Nombres que NO se traducen NUNCA: Thu'um, Thalmor, Daedra, Draugr, Nirn, Aedra, Alduin, Paarthurnax.
6. Mantiene EXACTAMENTE la estructura: mismas lineas, orden y saltos de linea.
7. Mantiene las etiquetas HTML/ESP intactas.
8. Mantiene las llaves {} y su contenido intactas cuando contengan etiquetas como <Global=...>.
9. Para terminos que NO aparecen en el CONTEXTO, traduce de la forma mas natural al espanol latino.
10. NO agregues notas, explicaciones ni comentarios. Solo la traduccion.
11. Se CONSISTENTE con las traducciones de nombres.

FORMATO DE SALIDA:
- Devuelve SOLO las lineas traducidas, en el mismo orden y cantidad que el original.""",
        "is_default": False
    },
    {
        "name": "Libros y Notas",
        "description": "Para traducir libros, cartas, notas y textos narrativos largos de Skyrim.",
        "content": """Eres un traductor experto de mods de Skyrim del ingles al espanol latino, especializado en libros, cartas y textos narrativos.

REGLAS OBLIGATORIAS:
1. Traduce TODO el texto al espanol con un tono literario y narrativo adecuado a libros de fantasia medieval.
2. Usa EXCLUSIVAMENTE la terminologia oficial de Skyrim que aparece en "TRADUCCIONES OBLIGATORIAS".
3. Si un nombre aparece en TRADUCCIONES OBLIGATORIAS, usa ESA traduccion EXACTA.
4. Nombres que NO se traducen NUNCA: Thu'um, Thalmor, Daedra, Draugr, Nirn, Aedra, Alduin, Paarthurnax.
5. Mantiene EXACTAMENTE la estructura: mismas lineas, orden y saltos de linea.
6. Mantiene las etiquetas HTML/ESP intactas.
7. Los libros de Skyrim usan un lenguaje arcaico y formal. Refleja ese estilo en la traduccion.
8. Para terminos que NO aparecen en el CONTEXTO, traduce de la forma mas natural al espanol latino.
9. NO agregues notas, explicaciones ni comentarios. Solo la traduccion.
10. Se CONSISTENTE con las traducciones de nombres.

FORMATO DE SALIDA:
- Devuelve SOLO las lineas traducidas, en el mismo orden y cantidad que el original.""",
        "is_default": False
    }
]


class PromptManager:
    def __init__(self, prompts_dir):
        self.prompts_dir = prompts_dir
        self.prompts_file = os.path.join(prompts_dir, "saved_prompts.json")
        self.prompts = {}
        os.makedirs(prompts_dir, exist_ok=True)
        self._load_all()

    def _load_all(self):
        if os.path.exists(self.prompts_file):
            try:
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    if isinstance(saved, list):
                        for p in saved:
                            if isinstance(p, dict) and p.get("name"):
                                self.prompts[p["name"]] = p
            except Exception as e:
                print(f"[AVISO] Error cargando prompts: {e}")
        for dp in [DEFAULT_PROMPT] + EXTRA_PROMPTS:
            if dp["name"] not in self.prompts:
                self.prompts[dp["name"]] = dp.copy()
        if not self.prompts:
            self.prompts[DEFAULT_PROMPT["name"]] = DEFAULT_PROMPT.copy()

    def _save(self):
        try:
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.prompts.values()), f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_names(self):
        return list(self.prompts.keys())

    def get_content(self, name):
        p = self.prompts.get(name)
        return p.get("content", "") if p else ""

    def get_info(self, name):
        p = self.prompts.get(name)
        if not p:
            return "", "", ""
        return p.get("description", ""), p.get("content", ""), "Si" if p.get("is_default") else "No"

    def add(self, name, description, content):
        if not name or not name.strip():
            return False, S.get("prompt_nombre_vacio")
        if not content or not content.strip():
            return False, S.get("prompt_contenido_vacio")
        name = name.strip()
        is_new = name not in self.prompts
        self.prompts[name] = {
            "name": name, "description": description.strip(), "content": content.strip(),
            "is_default": False,
            "created": time.strftime("%Y-%m-%d %H:%M") if is_new else self.prompts[name].get("created", ""),
            "modified": time.strftime("%Y-%m-%d %H:%M")
        }
        if self._save():
            act = S.get("prompt_creado") if is_new else S.get("prompt_actualizado")
            return True, f"Prompt '{name}' {act} correctamente"
        return False, "Error al guardar"

    def delete(self, name):
        if name not in self.prompts:
            return False, f"Prompt '{name}' no encontrado"
        if self.prompts[name].get("is_default"):
            return False, S.get("prompt_no_default")
        del self.prompts[name]
        if self._save():
            return True, f"Prompt '{name}' {S.get('prompt_eliminado')} correctamente"
        return False, "Error al guardar"


pm = PromptManager(PROMPTS_DIR)


# ============================================================
# DEPENDENCIAS
# ============================================================
def check_dependencies():
    for pkg in ["chromadb", "ollama", "gradio"]:
        try:
            m = __import__(pkg)
            print(f"  [OK] {pkg} {getattr(m, '__version__', '?')}")
        except ImportError:
            print(f"  [FALTA] {pkg}")
            sys.exit(1)


# ============================================================
# MOTOR RAG
# ============================================================
def get_chromadb_collection():
    import chromadb
    if not os.path.exists(CHROMA_DIR):
        sys.exit(1)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    c = client.get_collection(COLLECTION_NAME)
    print(f"ChromaDB: {c.count()} terminos")
    return c


def normalize_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', text.lower().strip()))


def search_terms(collection, text, n_results=CHROMA_SEARCH_LIMIT):
    results = collection.query(query_texts=[text], n_results=n_results)
    all_terms = []
    if results and results.get('metadatas') and results['metadatas']:
        for ml in results['metadatas']:
            if ml:
                for meta in ml:
                    en = meta.get("english", "").strip()
                    if not en:
                        continue
                    all_terms.append({"english": en, "spanish": meta.get("spanish", "").strip(),
                                      "category": meta.get("category", ""),
                                      "en_norm": normalize_text(en), "es_norm": normalize_text(meta.get("spanish", ""))})

    filtered = [t for t in all_terms if t["en_norm"] and t["en_norm"] != t["es_norm"]]
    unique = {}
    for t in filtered:
        k = t["en_norm"]
        if k not in unique or (len(t["english"]) < len(unique[k]["english"]) and t["spanish"]):
            unique[k] = t

    short = [t for t in unique.values() if len(t["english"].split()) <= 5]
    long = [t for t in unique.values() if len(t["english"].split()) > 5]
    final = short + long
    if len(final) > MAX_CONTEXT_TERMS:
        mx = MAX_CONTEXT_TERMS - 5
        final = (short[:mx] if len(short) > mx else short) + long[:5 if len(short) > mx else MAX_CONTEXT_TERMS - len(short)]
    return final


def build_context(terms):
    if not terms:
        return "CONTEXTO: No se encontraron terminos."
    short = [t for t in terms if len(t["english"].split()) <= 5]
    long = [t for t in terms if len(t["english"].split()) > 5]
    parts = []
    if short:
        parts += ["TRADUCCIONES OBLIGATORIAS (usa EXACTAMENTE estas):", "=" * 55]
        for t in short:
            en, es = t["english"], t["spanish"]
            parts.append(f"  {en} -> {es}  [NO TRADUCIR]" if es and normalize_text(en) == normalize_text(es) else f"  {en} -> {es}")
        parts += ["=" * 55, ""]
    if long:
        parts += ["ORACIONES DE REFERENCIA:", "-" * 55]
        cats = {}
        for t in long:
            cats.setdefault(t.get("category", "general"), []).append(t)
        for cat, cts in sorted(cats.items()):
            parts.append(f"[{cat.upper()}]")
            for t in cts[:3]:
                parts.append(f"  {t['english']} -> {t['spanish']}")
        parts.append("-" * 55)
    parts += ["", "REGLA: Si un nombre aparece en TRADUCCIONES OBLIGATORIAS, usa ESA traduccion en TODO el texto."]
    return "\n".join(parts)


def translate_with_ollama(text, context, system_prompt, model=OLLAMA_MODEL, temperature=TEMPERATURE):
    try:
        resp = ollama.chat(model=model, messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\nTEXTO A TRADUCIR:\n{text}"}
        ], options={"temperature": temperature, "num_predict": 8192})  # --- MODIFICADO: de 4096 a 8192 para textos largos ---
        return resp.message.content if hasattr(resp, 'message') else resp['message']['content']
    except Exception as e:
        if "connection" in str(e).lower() or "refused" in str(e).lower():
            return "[ERROR] No se puede conectar con Ollama. Verifica que este ejecutandose."
        return f"[ERROR] {e}"


def get_ollama_models():
    try:
        resp = ollama.list()
        names = []
        if hasattr(resp, 'models'):
            for m in resp.models:
                n = getattr(m, 'model', None) or getattr(m, 'name', None)
                if n:
                    names.append(n)
        elif isinstance(resp, dict):
            for m in resp.get('models', []):
                names.append(m.get('name', m.get('model', '')) if isinstance(m, dict) else str(m))
        return [n for n in names if n]
    except Exception:
        return []


# ============================================================
# INTERFAZ
# ============================================================
def create_interface():
    collection = get_chromadb_collection()
    try:
        models = get_ollama_models()
        print(f"Modelos: {models}")
    except Exception:
        pass

    # Config
    layout = config.get("layout", {})
    centrar_btn = layout.get("centrar_botones", True)
    alt_in = layout.get("altura_texto_entrada", 12)
    alt_out = layout.get("altura_texto_entrada", 12)
    mostrar_ln = layout.get("mostrar_lineas", True)
    fuentes = config.get("fuentes", {})
    ft = fuentes.get("titulo", "Segoe UI, sans-serif")
    fs = fuentes.get("tamano_titulo", "28px")
    fss = fuentes.get("tamano_subtitulo", "14px")
    colores = config.get("colores_personalizados", {})
    bg_t = colores.get("fondo_titulo", "#1a1a2e")
    tx_t = colores.get("texto_titulo", "#e0e0e0")

    # ---- Callbacks ----
    def line_counter(text, prefix_ln, prefix_ch):
        if not mostrar_ln:
            return ""
        n = len([l for l in (text or "").split('\n') if l.strip()])
        c = len(text or "")
        return f'<span style="background:#374151;color:#9ca3af;border-radius:6px;padding:2px 10px;font-size:12px;font-family:Consolas,monospace;">{prefix_ln}{n}  |  {prefix_ch}{c}</span>'

    def on_input_change(t):
        return line_counter(t, S.get("lineas_info_prefix", "Líneas: "), S.get("caracteres_info_prefix", "Caracteres: "))

    def on_output_change(t):
        return line_counter(t, S.get("lineas_info_prefix", "Líneas: "), S.get("caracteres_info_prefix", "Caracteres: "))

    # --- MODIFICADO: Se agrego parametro chunk_size para traduccion por fragmentos ---
    def do_translate(input_text, num_terms, prompt_name, chunk_size):
        if not input_text or not input_text.strip():
            return "", S.get("traduccion_sin_texto", "No se ingresó texto."), "", ""
        try:
            sp = pm.get_content(prompt_name) or DEFAULT_PROMPT["content"]
            terms = search_terms(collection, input_text, n_results=max(int(num_terms) * 3, CHROMA_SEARCH_LIMIT))
            ctx = build_context(terms)

            # --- NUEVO: Traduccion por fragmentos (chunking) ---
            # Si el texto tiene mas lineas que chunk_size, se divide en fragmentos
            # y cada uno se traduce por separado con el mismo contexto del glosario.
            # Esto evita que el modelo "olvide" las traducciones obligatorias en textos largos.
            lines = [l for l in input_text.split('\n')]
            chunk_sz = max(int(chunk_size), 1)

            if len(lines) <= chunk_sz:
                # Texto corto: traducir todo de una vez (comportamiento original)
                trans = translate_with_ollama(input_text, ctx, sp)
            else:
                # Texto largo: dividir en fragmentos y traducir cada uno
                chunks = []
                for i in range(0, len(lines), chunk_sz):
                    chunks.append('\n'.join(lines[i:i + chunk_sz]))

                print(f"  [CHUNK] {len(lines)} lineas -> {len(chunks)} fragmentos de ~{chunk_sz} lineas")

                translated_chunks = []
                for idx, chunk in enumerate(chunks):
                    print(f"  [CHUNK {idx+1}/{len(chunks)}] Traduciendo {len([l for l in chunk.split(chr(10)) if l.strip()])} lineas...")
                    chunk_trans = translate_with_ollama(chunk, ctx, sp)
                    if chunk_trans.startswith('[ERROR]'):
                        return chunk_trans, "Error en fragmento", ctx, ""
                    translated_chunks.append(chunk_trans.strip())

                trans = '\n'.join(translated_chunks)
            # --- FIN NUEVO: chunking ---

            sc = sum(1 for t in terms if len(t["english"].split()) <= 5)
            lc = len(terms) - sc
            # --- NUEVO: Mostrar info de fragmentos en el panel de terminos ---
            total_lines = len([l for l in lines if l.strip()])
            chunk_info = f" | Fragmentos: {(total_lines + chunk_sz - 1) // chunk_sz}" if total_lines > chunk_sz else ""
            td = f"Clave: {sc} | Referencia: {lc} | Prompt: {prompt_name}{chunk_info}\n\nTRADUCCIONES OBLIGATORIAS:\n"
            for t in terms:
                if len(t["english"].split()) <= 5:
                    en, es = t["english"], t["spanish"]
                    td += f"  {en} -> {es}\n" if es and normalize_text(en) != normalize_text(es) else f"  {en} [no traducir]\n"
            if lc:
                td += f"\nReferencia: {lc} (ver contexto)"
            return trans, td, ctx, on_output_change(trans)
        except Exception as e:
            return f"[ERROR] {e}", "Error", "", ""

    def refresh_list():
        names = pm.get_names()
        return gr.update(choices=names, value=names[0] if names else None)

    def on_prompt_sel(name):
        d, _, _ = pm.get_info(name)
        return d or "(sin descripción)"

    def on_load_edit(name):
        d, c, _ = pm.get_info(name)
        return name, d, c, f"Prompt '{name}' cargado para editar"

    def on_save(name, desc, content):
        ok, msg = pm.add(name, desc, content)
        return msg, refresh_list()

    def on_delete(name):
        _, msg = pm.delete(name)
        return msg, refresh_list()

    def on_new():
        return "", "", "", S.get("prompt_nuevo_msg")

    def on_dup(name):
        p = pm.prompts.get(name)
        if not p:
            return "", "", "", "Prompt no encontrado"
        return f"{name} (copia)", p.get("description", ""), p.get("content", ""), "Duplicado. Cambia el nombre y guarda."

    def on_list_change(name):
        d, c, df = pm.get_info(name)
        return f"<p><b>Nombre:</b> {name}</p><p><b>Descripción:</b> {d or '(sin descripción)'}</p><p><b>Por defecto:</b> {df}</p><p><b>Contenido:</b> {len(c)} caracteres</p>"

    def on_go_translate(prompt_name):
        names = pm.get_names()
        target = prompt_name if prompt_name in names else (names[0] if names else None)
        return gr.update(selected=0), gr.update(value=target)

    # --- MODIFICADO: CSS compacto para layout de 3 columnas ---
    custom_css = """
    .center-buttons { display: flex; justify-content: center; gap: 12px; margin-top: 8px; }
    .tooltip-container { position: relative; display: inline-flex; align-items: center; gap: 6px; }
    .tooltip-icon { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: #475569; color: #e2e8f0; font-size: 12px; font-weight: bold; cursor: help; }
    .tooltip-text { display: none; position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); background: #1e293b; color: #e2e8f0; padding: 10px 14px; border-radius: 6px; font-size: 13px; width: 300px; text-align: left; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.5); line-height: 1.5; }
    .tooltip-container:hover .tooltip-text { display: block; }
    .compact-controls { gap: 6px; }
    .compact-controls .gr-slider { min-width: 100% !important; }
    """

    # ---- Build UI ----
    prompt_names = pm.get_names()
    def_pn = prompt_names[0] if prompt_names else ""

    with gr.Blocks(title=config.get("titulo_pagina", "Skyrim Translation Agent"), css=custom_css) as interface:

        # Header
        gr.HTML(f"""
        <div style="text-align: center; margin-bottom: 10px; background: {bg_t}; padding: 16px; border-radius: 8px;">
            <h1 style="margin:0; color: {tx_t}; font-family: {ft}; font-size: {fs};">{S.get('titulo')}</h1>
            <p style="margin:6px 0 0 0; color: #9ca3af; font-size: {fss};">{S.get('subtitulo')}</p>
        </div>
        """)

        # Tabs contenedor (con referencia para navegacion)
        with gr.Tabs() as tabs:

            # ======== TAB 1: TRADUCIR ========
            # --- MODIFICADO: Layout de 3 columnas para que todo quepa sin scroll ---
            # Columna 1: Texto entrada | Columna 2: Controles compactos | Columna 3: Texto salida
            with gr.Tab(S.get("tab_traducir")):
                with gr.Row(equal_height=True):
                    # ---- Columna 1: Entrada ----
                    with gr.Column(scale=5):
                        input_text = gr.Textbox(
                            label=f"{S.get('panel_entrada_titulo')} — {S.get('panel_entrada_descripcion')}",
                            placeholder=S.get("panel_entrada_placeholder"),
                            lines=7  # --- MODIFICADO: de alt_in (12) a 7 para que quepa todo
                        )
                        input_counter = gr.HTML(value=on_input_change(""))

                    # ---- Columna 2: Controles compactos ----
                    with gr.Column(scale=3, elem_classes=["compact-controls"]):
                        # Slider de terminos de contexto
                        with gr.Row():
                            gr.HTML(f"""
                            <div class="tooltip-container">
                                <span style="font-weight: 600; font-size: 13px;">{S.get('slider_terminos_label')}</span>
                                <span class="tooltip-icon">?</span>
                                <span class="tooltip-text">{S.get('slider_terminos_tooltip')}</span>
                            </div>
                            """)
                        # --- MODIFICADO: maximo aumentado de 50 a 100 ---
                        num_terms = gr.Slider(minimum=10, maximum=100, value=30, step=5, label="")

                        # Slider de lineas por fragmento
                        with gr.Row():
                            gr.HTML(f"""
                            <div class="tooltip-container">
                                <span style="font-weight: 600; font-size: 13px;">Lineas por traduccion</span>
                                <span class="tooltip-icon">?</span>
                                <span class="tooltip-text">Texto largo se divide en fragmentos de este tamano. Menos lineas = mejor calidad (el modelo sigue el glosario), pero mas lento. Mas lineas = mas rapido, pero puede perder terminologia. Recomendado: 8 para precision, 15 para rapidez.</span>
                            </div>
                            """)
                        chunk_size = gr.Slider(minimum=3, maximum=20, value=DEFAULT_CHUNK_SIZE, step=1, label="")

                        # Selector de prompt
                        with gr.Row():
                            prompt_selector = gr.Dropdown(
                                choices=prompt_names, value=def_pn,
                                label=S.get("selector_prompt_label"), scale=3, allow_custom_value=False
                            )
                            prompt_refresh_btn = gr.Button(S.get("selector_prompt_refrescar"), variant="secondary", scale=1)

                        prompt_desc_display = gr.Textbox(
                            label=S.get("descripcion_prompt_label"),
                            value=pm.get_info(def_pn)[0] or "(sin descripcion)",
                            interactive=False, lines=1
                        )

                        # Botones traducir y limpiar
                        with gr.Row(elem_classes=["center-buttons"]):
                            translate_btn = gr.Button(S.get("btn_traducir"), variant="primary", size="lg")
                            clear_btn = gr.Button(S.get("btn_limpiar"), variant="secondary", size="lg")

                    # ---- Columna 3: Salida ----
                    with gr.Column(scale=5):
                        output_text = gr.Textbox(
                            label=f"{S.get('panel_salida_titulo')} — {S.get('panel_salida_descripcion')}",
                            placeholder=S.get("panel_salida_placeholder"),
                            lines=7  # --- MODIFICADO: de alt_out (12) a 7 para que quepa todo
                        )
                        output_counter = gr.HTML(value=on_output_change(""))

                # Acordiones de debug (colapsados por defecto, debajo de todo)
                with gr.Accordion(S.get("accordion_terminos_titulo"), open=False):
                    terms_info = gr.Textbox(label=S.get("accordion_terminos_label"), lines=6)

                with gr.Accordion(S.get("accordion_contexto_titulo"), open=False):
                    context_info = gr.Textbox(label=S.get("accordion_contexto_label"), lines=8)

            # ======== TAB 2: PROMPTS ========
            with gr.Tab(S.get("tab_prompts")):
                gr.Markdown(S.get("prompts_seccion_descripcion"))

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown(f"### {S.get('prompts_lista_titulo')}")
                        prompt_list_dd = gr.Dropdown(
                            choices=prompt_names, value=def_pn,
                            label=S.get("prompts_lista_label"), allow_custom_value=False
                        )
                        prompt_list_info = gr.HTML(value="<p style='color:#888;'>Selecciona un prompt</p>")

                        with gr.Row():
                            load_edit_btn = gr.Button(S.get("prompts_cargar_btn"), variant="primary", scale=1)
                            dup_btn = gr.Button(S.get("prompts_duplicar_btn"), variant="secondary", scale=1)
                        with gr.Row():
                            del_btn = gr.Button(S.get("prompts_eliminar_btn"), variant="stop", scale=1)
                            new_btn = gr.Button(S.get("prompts_nuevo_btn"), variant="secondary", scale=1)
                        with gr.Column(scale=2):
                            gr.Markdown(f"### {S.get('prompts_editor_titulo')}")
                            save_btn = gr.Button(S.get("prompts_guardar_btn"), variant="primary", size="lg")
                            go_btn = gr.Button(S.get("prompts_probar_btn"), variant="secondary", size="lg")
                            ep_status = gr.Textbox(label=S.get("prompts_estado_label"), interactive=False, lines=1)

                    with gr.Column(scale=2):
                        gr.Markdown(f"### {S.get('prompts_editor_titulo')}")
                        ep_name = gr.Textbox(label=S.get("prompts_nombre_label"), placeholder=S.get("prompts_nombre_placeholder"), lines=1)
                        ep_desc = gr.Textbox(label=S.get("prompts_desc_label"), placeholder=S.get("prompts_desc_placeholder"), lines=2)
                        ep_content = gr.Textbox(label=S.get("prompts_contenido_label"), placeholder=S.get("prompts_contenido_placeholder"), lines=15)
                        
                            
                            

        # Footer
        gr.HTML(f"""
        <div style="text-align: center; font-size: 12px; color: #888; margin-top: 20px;">
            <p>{S.get('footer_flujo')}</p>
            <p>Motor: Ollama + ChromaDB + RAG | Modelo: {OLLAMA_MODEL} | Prompts: {len(prompt_names)}</p>
        </div>
        """)

        # ======== EVENTOS - Traduccion ========
        # --- MODIFICADO: Se agrego chunk_size como input del boton traducir ---
        translate_btn.click(fn=do_translate, inputs=[input_text, num_terms, prompt_selector, chunk_size],
                           outputs=[output_text, terms_info, context_info, output_counter])

        clear_btn.click(
            fn=lambda: ("", "", "", on_input_change("")),
            inputs=[], outputs=[input_text, output_text, terms_info, input_counter]
        )

        input_text.change(fn=on_input_change, inputs=[input_text], outputs=[input_counter])
        output_text.change(fn=on_output_change, inputs=[output_text], outputs=[output_counter])
        prompt_selector.change(fn=on_prompt_sel, inputs=[prompt_selector], outputs=[prompt_desc_display])
        prompt_refresh_btn.click(fn=lambda: refresh_list(), inputs=[], outputs=[prompt_selector])

        # ======== EVENTOS - Prompts ========
        prompt_list_dd.change(fn=on_list_change, inputs=[prompt_list_dd], outputs=[prompt_list_info])
        load_edit_btn.click(fn=on_load_edit, inputs=[prompt_list_dd], outputs=[ep_name, ep_desc, ep_content, ep_status])
        dup_btn.click(fn=on_dup, inputs=[prompt_list_dd], outputs=[ep_name, ep_desc, ep_content, ep_status])
        save_btn.click(fn=on_save, inputs=[ep_name, ep_desc, ep_content], outputs=[ep_status, prompt_list_dd])
        del_btn.click(fn=on_delete, inputs=[prompt_list_dd], outputs=[ep_status, prompt_list_dd])
        new_btn.click(fn=on_new, inputs=[], outputs=[ep_name, ep_desc, ep_content, ep_status])

        # Boton "Ir a Traducir" - navega al tab 0 y selecciona el prompt
        go_btn.click(fn=on_go_translate, inputs=[ep_name], outputs=[tabs, prompt_selector])

    return interface


# ============================================================
# INICIO
# ============================================================
def main():
    print("=" * 60)
    print("SERVIDOR DE TRADUCCION SKYRIM")
    print("=" * 60)
    print("\nVerificando dependencias...")
    check_dependencies()
    print(f"\nModelo: {OLLAMA_MODEL}")
    print(f"BD:     {CHROMA_DIR}")
    print(f"Config: {CONFIG_FILE}")
    print(f"Strings:{STRINGS_FILE}")
    print(f"Puerto: {GRADIO_PORT}")
    print(f"\nhttp://localhost:{GRADIO_PORT}")
    print("=" * 60)

    try:
        interface = create_interface()
        kwargs = {"server_name": "0.0.0.0", "server_port": GRADIO_PORT, "share": False, "inbrowser": True}
        try:
            tema = config.get("tema", "Soft")
            color = config.get("color_primario", "blue")
            tema_map = {"Soft": gr.themes.Soft, "Default": gr.themes.Default, "Base": gr.themes.Base,
                        "Glass": gr.themes.Glass, "Monochrome": gr.themes.Monochrome}
            kwargs["theme"] = tema_map.get(tema, gr.themes.Soft)(primary_hue=color)
        except Exception:
            pass
        interface.launch(**kwargs)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
        input("Presiona Enter para cerrar...")


if __name__ == "__main__":
    main()

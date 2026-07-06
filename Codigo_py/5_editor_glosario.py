"""
=====================================================
EDITOR DE GLOSARIO - Interfaz grafica para crear
y editar archivos JSON de terminologia Skyrim
=====================================================

Compatible con:
  - Python 3.11.9
  - ollama >= 0.4.0
  - Gradio >= 6.0
  - chromadb >= 1.0

Permite crear, cargar, editar y guardar archivos JSON
con pares de texto ingles/espanol para el glosario.

USO: python 5_editor_glosario.py
Luego abre en el navegador: http://localhost:7861
"""

import os
import sys
import json
import traceback

# Importar gradio al nivel del modulo para que este disponible en todo el archivo
import gradio as gr

# ============================================================
# CONFIGURACION
# ============================================================
# Detectar BASE_DIR automaticamente: si estamos en Codigo_py/, subir un nivel
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(_SCRIPT_DIR, "BD")):
    BASE_DIR = _SCRIPT_DIR
elif os.path.exists(os.path.join(_SCRIPT_DIR, "..", "BD")):
    BASE_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
else:
    BASE_DIR = _SCRIPT_DIR
BD_DIR = os.path.join(BASE_DIR, "BD")
GRADIO_PORT = 7861

# --- NUEVO: Ruta de strings multilenguaje para el editor ---
STRINGS_DIR = os.path.join(BASE_DIR, "editor_config", "strings")

# --- NUEVO: Sistema multilenguaje ---
def get_available_languages():
    """Retorna dict {codigo: nombre} de idiomas disponibles."""
    langs = {"es": "Español"}
    if os.path.exists(STRINGS_DIR):
        for fname in os.listdir(STRINGS_DIR):
            if fname.endswith('.json'):
                code = fname[:-5]
                try:
                    with open(os.path.join(STRINGS_DIR, fname), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        langs[code] = data.get("lang_name", code.upper())
                except Exception:
                    langs[code] = code.upper()
    return langs

def load_language(lang_code):
    """Carga strings del idioma especificado."""
    lang_file = os.path.join(STRINGS_DIR, f"{lang_code}.json")
    if os.path.exists(lang_file):
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[AVISO] Error cargando idioma {lang_code}: {e}")
    # Fallback basico
    return {
        "lang_name": lang_code.upper(),
        "titulo": "Skyrim Glossary Editor",
        "subtitulo": "Create and edit JSON terminology files",
        "lang_label": "Language"
    }

AVAILABLE_LANGS = get_available_languages()
DEFAULT_LANG = "es"
S = load_language(DEFAULT_LANG)

CATEGORIES = [
    "general", "lugar", "npc", "objeto", "arma", "armadura",
    "magia", "hechizo", "criatura", "faction", "quest", "raza",
    "habilidad", "perk", "libro", "dialogo", "interfaz", "otro",
]

TYPES = ["nombre", "verbo", "adjetivo", "frase", "dialogo", "descripcion", "otro"]

CATEGORY_COLORS = {
    "lugar": "#4CAF50", "npc": "#FF9800", "objeto": "#2196F3",
    "arma": "#F44336", "armadura": "#9C27B0", "magia": "#00BCD4",
    "hechizo": "#009688", "criatura": "#795548", "faction": "#607D8B",
    "quest": "#FFC107", "raza": "#E91E63", "habilidad": "#3F51B5",
    "perk": "#8BC34A", "libro": "#FF5722", "dialogo": "#CDDC39",
    "interfaz": "#9E9E9E", "general": "#616161", "otro": "#9E9E9E",
}


# ============================================================
# ESTADO GLOBAL
# ============================================================
class GlossaryState:
    def __init__(self):
        self.entries = []
        self.filename = ""
        self.filepath = ""
        self.modified = False
        self.selected_index = -1
        # --- NUEVO: indices de la ultima busqueda para mapear fila visible -> entrada real ---
        self.filtered_indices = []  # Lista de indices reales en state.entries
        # --- NUEVO: campo de traduccion dinamico (se detecta al cargar JSON) ---
        self.translation_field = "spanish"  # Valor por defecto para compatibilidad

    def reset(self):
        self.entries = []
        self.filename = ""
        self.filepath = ""
        self.modified = False
        self.selected_index = -1
        self.filtered_indices = []  # --- NUEVO ---
        # NO reseteamos translation_field para mantenerlo entre operaciones

    def add_entry(self, english, translation, category="general", entry_type="", source="manual"):
        entry = {
            "english": english.strip(),
            self.translation_field: translation.strip(),
            "category": category or "general",
            "type": entry_type or "",
            "source": source or "manual"
        }
        self.entries.append(entry)
        self.modified = True
        return len(self.entries) - 1

    def update_entry(self, index, english, translation, category, entry_type, source):
        if 0 <= index < len(self.entries):
            self.entries[index] = {
                "english": english.strip(),
                self.translation_field: translation.strip(),
                "category": category or "general",
                "type": entry_type or "",
                "source": source or "manual"
            }
            self.modified = True
            return True
        return False

    def delete_entry(self, index):
        if 0 <= index < len(self.entries):
            del self.entries[index]
            self.modified = True
            return True
        return False

    def move_entry(self, index, direction):
        if direction == "up" and index > 0:
            self.entries[index], self.entries[index-1] = self.entries[index-1], self.entries[index]
            self.modified = True
            return index - 1
        elif direction == "down" and index < len(self.entries) - 1:
            self.entries[index], self.entries[index+1] = self.entries[index+1], self.entries[index]
            self.modified = True
            return index + 1
        return index

    def _detect_translation_field(self, entries):
        """Detecta el campo de traduccion buscando el primer campo que no sea
        english, category, type, o source."""
        if not entries:
            return "spanish"  # fallback por defecto
        first_entry = entries[0]
        known_fields = {"english", "category", "type", "source"}
        for key in first_entry.keys():
            if key not in known_fields:
                return key
        return "spanish"  # fallback por defecto

    def load_from_json(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            self.entries = data
        elif isinstance(data, dict):
            # Formato con metadata (compatibilidad hacia atras)
            if "entries" in data:
                self.entries = data["entries"]
            else:
                self.entries = []
                for key, value in data.items():
                    if isinstance(value, list):
                        self.entries.extend(value)
        # Detectar el campo de traduccion automaticamente
        self.translation_field = self._detect_translation_field(self.entries)
        self.filename = os.path.basename(filepath)
        self.filepath = filepath
        self.modified = False
        return len(self.entries)

    def save_to_json(self, filepath=None):
        if filepath:
            self.filepath = filepath
            self.filename = os.path.basename(filepath)
        if not self.filepath:
            return False
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)
        self.modified = False
        return True

    def search_entries(self, query):
        if not query.strip():
            return list(range(len(self.entries)))
        query_lower = query.lower()
        results = []
        for i, entry in enumerate(self.entries):
            if (query_lower in entry.get("english", "").lower() or
                query_lower in entry.get(self.translation_field, "").lower() or
                query_lower in entry.get("category", "").lower()):
                results.append(i)
        return results


state = GlossaryState()


# ============================================================
# FUNCIONES DE RENDERIZADO
# ============================================================

def render_line_preview(entries, highlight_idx=-1):
    if not entries:
        return '<div style="text-align:center; color:#888; padding:40px;"><p>No hay entradas en el glosario</p></div>'

    html_parts = ['<div style="font-family: Consolas, monospace; font-size: 14px; background: #1e1e1e; border-radius: 8px; padding: 12px; color: #d4d4d4; max-height: 600px; overflow-y: auto;">']
    for i, entry in enumerate(entries):
        en_text = entry.get("english", "").replace("<", "&lt;").replace(">", "&gt;")
        tr_text = entry.get(state.translation_field, "").replace("<", "&lt;").replace(">", "&gt;")
        cat = entry.get("category", "")
        bg = " background:#3a3a2a;" if i == highlight_idx else ""
        cat_color = CATEGORY_COLORS.get(cat, "#608b4e")
        html_parts.append(f'<div style="display:flex; padding:3px 0; border-bottom:1px solid #333;{bg}">'
                          f'<span style="color:#858585; min-width:40px; text-align:right; padding-right:12px; user-select:none;">{i+1}</span>'
                          f'<span style="color:#9cdcfe; flex:1; padding-right:20px; word-break:break-word;">{en_text}</span>'
                          f'<span style="color:#569cd6; padding:0 8px; user-select:none;">&rarr;</span>'
                          f'<span style="color:#ce9178; flex:1; word-break:break-word;">{tr_text}</span>'
                          f'<span style="color:{cat_color}; font-size:11px; padding-left:10px; min-width:70px; text-align:right;">[{cat}]</span>'
                          f'</div>')
    html_parts.append('</div>')
    return "\n".join(html_parts)


def render_stats(entries):
    if not entries:
        return "<p style='color:#888;'>Sin entradas</p>"
    cats = {}
    for e in entries:
        c = e.get("category", "sin_categoria")
        cats[c] = cats.get(c, 0) + 1
    total = len(entries)
    mod = ' <span style="color:#FF9800;">[MODIFICADO]</span>' if state.modified else ""
    html = f'<div style="padding:8px;"><p style="margin:0 0 8px 0; font-size:16px; font-weight:bold;">{total} entradas{mod}</p><div style="display:flex; flex-wrap:wrap; gap:8px;">'
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        color = CATEGORY_COLORS.get(cat, "#616161")
        html += f'<span style="background:{color}22; color:{color}; border:1px solid {color}44; border-radius:12px; padding:2px 10px; font-size:12px;">{cat}: {count}</span>'
    html += "</div></div>"
    return html


# ============================================================
# CALLBACKS
# ============================================================

def new_glossary(filename):
    state.reset()
    # --- NUEVO: filtered_indices ya se limpia en reset() ---
    if filename and filename.strip():
        safe_name = filename.strip()
        if not safe_name.endswith('.json'):
            safe_name += '.json'
        state.filename = safe_name
        state.filepath = os.path.join(BD_DIR, safe_name)
    return (render_line_preview(state.entries), render_stats(state.entries),
            f"Nuevo glosario: {state.filename or 'sin nombre'}",
            None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "")


def _translation_field_label():
    """Retorna un nombre visible para el campo de traduccion actual."""
    field = state.translation_field
    # Capitalizar primera letra, reemplazar underscores por espacios
    return field.replace("_", " ").title()


def load_json_file(file_obj):
    """Carga un JSON y actualiza la UI incluyendo labels del campo de traduccion."""
    # Valores por defecto para los labels de traduccion
    tr_label = _translation_field_label()
    default_labels = (
        gr.update(label=tr_label),           # edit_es label
        gr.update(label=tr_label),           # single_es label
        gr.update(value=f"### {tr_label}"),  # agregar_esp_titulo_md
    )

    if file_obj is None:
        return (render_line_preview(state.entries), render_stats(state.entries),
                "No se selecciono ningun archivo", None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "",
                *default_labels)

    filepath = file_obj.name if hasattr(file_obj, 'name') else str(file_obj)
    try:
        count = state.load_from_json(filepath)
        state.filtered_indices = []
        tr_label = _translation_field_label()

        # Generar headers dinamicos para el Dataframe
        tabla_headers = f"#|English|{tr_label}|Category|Type|Source"

        return (render_line_preview(state.entries), render_stats(state.entries),
                f"Cargado: {state.filename} ({count} entradas, campo: {state.translation_field})",
                None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "",
                gr.update(label=tr_label),                   # edit_es label
                gr.update(label=tr_label),                   # single_es label
                gr.update(value=f"### {tr_label}"),         # agregar_esp_titulo_md
                )
    except Exception as e:
        return (render_line_preview(state.entries), render_stats(state.entries),
                f"Error al cargar: {str(e)}", None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "",
                *default_labels)


def save_json_file(filename):
    if not state.entries:
        return render_line_preview(state.entries), render_stats(state.entries), "No hay entradas para guardar", state.filename or ""
    if filename and filename.strip():
        safe_name = filename.strip()
        if not safe_name.endswith('.json'):
            safe_name += '.json'
        filepath = os.path.join(BD_DIR, safe_name)
        state.filename = safe_name
    elif state.filepath:
        filepath = state.filepath
    else:
        return render_line_preview(state.entries), render_stats(state.entries), "Escribe un nombre de archivo", state.filename or ""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        state.save_to_json(filepath)
        return render_line_preview(state.entries), render_stats(state.entries), f"Guardado: {state.filename} ({len(state.entries)} entradas)", state.filename or ""
    except Exception as e:
        return render_line_preview(state.entries), render_stats(state.entries), f"Error: {str(e)}", state.filename or ""


def add_lines_from_textarea(en_text, es_text, category, source):
    en_text = en_text or ""
    es_text = es_text or ""
    if not en_text.strip() and not es_text.strip():
        return render_line_preview(state.entries), render_stats(state.entries), "Escribe texto para agregar", "", ""
    en_lines = [l for l in en_text.split('\n') if l.strip()]
    es_lines = [l for l in es_text.split('\n') if l.strip()]
    added = 0
    for i in range(max(len(en_lines), len(es_lines))):
        en = en_lines[i] if i < len(en_lines) else ""
        es = es_lines[i] if i < len(es_lines) else ""
        if en.strip() or es.strip():
            state.add_entry(en.strip(), es.strip(), category, "", source)
            added += 1
    return render_line_preview(state.entries), render_stats(state.entries), f"Agregadas {added} entradas. Total: {len(state.entries)}", "", ""


def add_single_line(en_text, es_text, category, entry_type, source):
    en_text = en_text or ""
    es_text = es_text or ""
    if not en_text.strip() and not es_text.strip():
        return render_line_preview(state.entries), render_stats(state.entries), "Escribe al menos ingles o espanol", "", ""
    state.add_entry(en_text.strip(), es_text.strip(), category, entry_type, source)
    return render_line_preview(state.entries), render_stats(state.entries), f"Agregada entrada #{len(state.entries)}", "", ""


def search_entries(query):
    if not state.entries:
        return None, "No hay entradas para buscar"
    indices = state.search_entries(query or "")
    if not indices:
        # --- MODIFICADO: limpiar indices filtrados cuando no hay resultados ---
        state.filtered_indices = []
        return None, f"No se encontraron resultados para '{query}'"
    # --- MODIFICADO: guardar indices reales para que on_table_select los use ---
    state.filtered_indices = indices
    table_data = [[idx+1, state.entries[idx].get("english",""), state.entries[idx].get(state.translation_field,""),
                    state.entries[idx].get("category","general"), state.entries[idx].get("type",""),
                    state.entries[idx].get("source","manual")] for idx in indices]
    return table_data, f"Encontradas {len(table_data)} entradas"


def on_table_select(evt: gr.SelectData):
    try:
        # --- MODIFICADO: usar indice real desde filtered_indices, no la fila visible ---
        display_row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index

        # Si hay indices filtrados, mapear fila visible -> indice real en state.entries
        if state.filtered_indices and 0 <= display_row < len(state.filtered_indices):
            real_index = state.filtered_indices[display_row]
        else:
            # Si no hay busqueda activa, la fila visible = indice real
            real_index = display_row

        if state.entries and 0 <= real_index < len(state.entries):
            entry = state.entries[real_index]
            state.selected_index = real_index
            return (entry.get("english",""), entry.get(state.translation_field,""),
                    entry.get("category","general") or CATEGORIES[0],
                    entry.get("type","") or TYPES[0],
                    entry.get("source","manual"), real_index)
    except Exception as e:
        print(f"Error al seleccionar: {e}")
    return "", "", CATEGORIES[0], TYPES[0], "manual", -1


def save_edited_entry(english, spanish, category, entry_type, source, index):
    try:
        index = int(index) if index is not None else -1
    except (ValueError, TypeError):
        index = -1
    if index < 0:
        return render_line_preview(state.entries), render_stats(state.entries), "No hay entrada seleccionada", "", "", CATEGORIES[0], TYPES[0], "manual", -1
    state.update_entry(index, english or "", spanish or "", category, entry_type, source)
    state.selected_index = -1
    return render_line_preview(state.entries), render_stats(state.entries), f"Entrada #{index+1} actualizada", "", "", CATEGORIES[0], TYPES[0], "manual", -1


def delete_selected_entry(index):
    try:
        index = int(index) if index is not None else -1
    except (ValueError, TypeError):
        index = -1
    if index < 0:
        return render_line_preview(state.entries), render_stats(state.entries), "No hay entrada seleccionada", "", "", CATEGORIES[0], TYPES[0], "manual", -1
    state.delete_entry(int(index))
    return render_line_preview(state.entries), render_stats(state.entries), f"Entrada eliminada. Quedan {len(state.entries)}", "", "", CATEGORIES[0], TYPES[0], "manual", -1


def move_selected_entry(index, direction):
    try:
        index = int(index) if index is not None else -1
    except (ValueError, TypeError):
        index = -1
    if index < 0:
        return render_line_preview(state.entries), render_stats(state.entries), "No hay entrada seleccionada"
    new_idx = state.move_entry(int(index), direction)
    return render_line_preview(state.entries, highlight_idx=new_idx), render_stats(state.entries), f"Movida {'arriba' if direction=='up' else 'abajo'}. Posicion: #{new_idx+1}"


def load_all_existing_jsons():
    if not os.path.exists(BD_DIR):
        return "Carpeta BD no encontrada"
    json_files = [f for f in os.listdir(BD_DIR) if f.endswith('.json') and f != 'skyrim_glossary_en_es.json']
    if not json_files:
        return "No se encontraron archivos JSON adicionales en la carpeta BD"
    result = "Archivos JSON encontrados en BD/:\n\n"
    for f in json_files:
        filepath = os.path.join(BD_DIR, f)
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                count = len(data) if isinstance(data, list) else "?"
                result += f"  {f} ({count} entradas)\n"
        except Exception:
            result += f"  {f} (error al leer)\n"
    result += "\nUsa 'Cargar JSON' para abrir uno de estos archivos."
    return result


# ============================================================
# INTERFAZ GRAFICA (Gradio 6.x compatible)
# ============================================================

def create_interface():
    # --- NUEVO: Funcion para cambiar idioma dinamicamente ---
    def on_lang_change(lang_code):
        global S
        S = load_language(lang_code)
        # Retornar actualizaciones para todos los componentes de UI
        # gr.Tab se actualiza con gr.update(label=...) igual que el servidor de traduccion
        return (
            # 0: Header HTML
            gr.update(value=f'<div style="text-align:center; margin-bottom:5px;"><h1 style="margin:0; color:#d4a017;">{S.get("titulo")}</h1>'
                f'<p style="margin:4px 0 0 0; color:#888; font-size:14px;">{S.get("subtitulo")}</p></div>'),
            # 1: Filename input
            gr.update(label=S.get("filename_label"), placeholder=S.get("filename_placeholder")),
            # 2: Nuevo btn
            gr.update(value=S.get("btn_nuevo")),
            # 3: Guardar btn
            # NOTA: load_btn (UploadButton) NO se incluye porque gr.update(value=texto)
            #       lo trata como ruta de archivo y causa FileNotFoundError
            gr.update(value=S.get("btn_guardar")),
            # 4: Buscar jsons btn
            gr.update(value=S.get("btn_buscar_jsons")),
            # 5: Tab Buscar
            gr.update(label=S.get("tab_buscar")),
            # 6: Buscar descripcion markdown
            gr.update(value=S.get("buscar_descripcion")),
            # 7: Search input
            gr.update(label=S.get("buscar_label"), placeholder=S.get("buscar_placeholder")),
            # 8: Search btn
            gr.update(value=S.get("btn_buscar")),
            # 9: Ver todas btn
            gr.update(value=S.get("btn_ver_todas")),
            # 10: Search status label
            gr.update(label=S.get("resultado_label")),
            # 11: Search results Dataframe (label + headers dinamicos)
            gr.update(label=S.get("tabla_label"),
                      headers=f"#|English|{_translation_field_label()}|Category|Type|Source".split("|")),
            # 12: Edit en
            gr.update(label=S.get("edit_ingles"), placeholder=S.get("edit_placeholder")),
            # 13: Edit es (usa translation_field dinamico)
            gr.update(label=_translation_field_label(), placeholder="..."),
            # 14: Edit cat
            gr.update(label=S.get("edit_categoria")),
            # 15: Edit type
            gr.update(label=S.get("edit_tipo")),
            # 16: Edit source
            gr.update(label=S.get("edit_fuente")),
            # 17: Acciones titulo markdown
            gr.update(value=f"### {S.get('acciones_titulo')}"),
            # 18: Guardar cambios btn
            gr.update(value=S.get("btn_guardar_cambios")),
            # 19: Eliminar btn
            gr.update(value=S.get("btn_eliminar")),
            # 20: Subir btn
            gr.update(value=S.get("btn_subir")),
            # 21: Bajar btn
            gr.update(value=S.get("btn_bajar")),
            # 22: Tab Agregar
            gr.update(label=S.get("tab_agregar")),
            # 23: Agregar descripcion markdown
            gr.update(value=S.get("agregar_descripcion")),
            # 24: Agregar ingles titulo markdown
            gr.update(value=f"### {S.get('agregar_ingles_titulo')}"),
            # 25: En textarea placeholder
            gr.update(placeholder=S.get("agregar_ingles_placeholder")),
            # 26: Agregar espanol titulo markdown (usa translation_field dinamico)
            gr.update(value=f"### {_translation_field_label()}"),
            # 27: Es textarea placeholder
            gr.update(placeholder=S.get("agregar_espanol_placeholder")),
            # 28: Cat dropdown label
            gr.update(label=S.get("agregar_categoria_label")),
            # 29: Source input
            gr.update(label=S.get("agregar_fuente_label"), placeholder=S.get("agregar_fuente_placeholder")),
            # 30: Add lines btn
            gr.update(value=S.get("btn_agregar_todas")),
            # 31: Single titulo markdown
            gr.update(value=f"### {S.get('agregar_single_titulo')}"),
            # 32: Single en
            gr.update(label=S.get("single_ingles"), placeholder=S.get("single_ingles_placeholder")),
            # 33: Single es (usa translation_field dinamico)
            gr.update(label=_translation_field_label(), placeholder=S.get("single_espanol_placeholder")),
            # 34: Single cat
            gr.update(label=S.get("edit_categoria")),
            # 35: Single type
            gr.update(label=S.get("edit_tipo")),
            # 36: Single source
            gr.update(label=S.get("edit_fuente"), placeholder=S.get("single_fuente_placeholder")),
            # 37: Add single btn
            gr.update(value=S.get("btn_agregar")),
            # 38: Tab Vista
            gr.update(label=S.get("tab_vista")),
            # 39: Vista descripcion markdown
            gr.update(value=S.get("vista_descripcion")),
            # 40: Tab Archivos
            gr.update(label=S.get("tab_archivos")),
            # 41: Archivos descripcion markdown
            gr.update(value=S.get("archivos_descripcion")),
            # 42: Json list label
            gr.update(label=S.get("archivos_label")),
            # 43: Refresh jsons btn
            gr.update(value=S.get("btn_actualizar_lista")),
        )

    # Gradio 6.x: NO pasar theme ni css a Blocks(), van en launch()
    with gr.Blocks(title="Editor de Glosario Skyrim") as interface:

        # --- NUEVO: Selector de idioma + Header ---
        with gr.Row():
            lang_dropdown = gr.Dropdown(
                choices=[(name, code) for code, name in AVAILABLE_LANGS.items()],
                value=DEFAULT_LANG,
                label=S.get("lang_label"), scale=1, min_width=150, allow_custom_value=False
            )
            gr.Column(scale=5)  # spacer

        header_html = gr.HTML(f'<div style="text-align:center; margin-bottom:5px;"><h1 style="margin:0; color:#d4a017;">{S.get("titulo")}</h1><p style="margin:4px 0 0 0; color:#888; font-size:14px;">{S.get("subtitulo")}</p></div>')

        with gr.Row():
            filename_input = gr.Textbox(label=S.get("filename_label"), placeholder=S.get("filename_placeholder"), value="", scale=3)
            new_btn = gr.Button(S.get("btn_nuevo"), variant="secondary", scale=1)
            load_btn = gr.UploadButton(S.get("btn_cargar"), file_types=[".json"], variant="secondary", scale=1)
            save_btn = gr.Button(S.get("btn_guardar"), variant="primary", scale=1)
            scan_btn = gr.Button(S.get("btn_buscar_jsons"), variant="secondary", scale=1)

        status_text = gr.HTML(value=f"<p style='color:#888;'>{S.get('status_listo')}</p>")
        stats_html = gr.HTML(value=render_stats(state.entries))

        with gr.Tabs(selected="tab_buscar") as tabs:

            # TAB 1: Buscar y Editar (pestaña principal por defecto)
            tab_buscar = gr.Tab(S.get("tab_buscar"), id="tab_buscar")
            with tab_buscar:
                buscar_desc_md = gr.Markdown(S.get("buscar_descripcion"))
                with gr.Row():
                    search_input = gr.Textbox(label=S.get("buscar_label"), placeholder=S.get("buscar_placeholder"), scale=4)
                    search_btn = gr.Button(S.get("btn_buscar"), variant="primary", scale=1)
                    search_all_btn = gr.Button(S.get("btn_ver_todas"), variant="secondary", scale=1)

                search_status = gr.Textbox(label=S.get("resultado_label"), value="", interactive=False)
                search_results = gr.Dataframe(
                    headers=["#", "English", _translation_field_label(), "Category", "Type", "Source"],
                    label=S.get("tabla_label"),
                    interactive=False, wrap=True
                )

                with gr.Row():
                    with gr.Column(scale=3):
                        edit_index_hidden = gr.Number(value=-1, visible=False, precision=0)
                        with gr.Row():
                            edit_en = gr.Textbox(label=S.get("edit_ingles"), placeholder=S.get("edit_placeholder"), scale=1)
                            edit_es = gr.Textbox(label=_translation_field_label(), placeholder="...", scale=1)
                        with gr.Row():
                            edit_cat = gr.Dropdown(choices=CATEGORIES, value=CATEGORIES[0], label=S.get("edit_categoria"), scale=1)
                            edit_type = gr.Dropdown(choices=TYPES, value=TYPES[0], label=S.get("edit_tipo"), scale=1)
                            edit_source = gr.Textbox(label=S.get("edit_fuente"), value="manual", scale=1)
                    with gr.Column(scale=1, min_width=120):
                        acciones_titulo_md = gr.Markdown(f"### {S.get('acciones_titulo')}")
                        save_edit_btn = gr.Button(S.get("btn_guardar_cambios"), variant="primary")
                        delete_btn = gr.Button(S.get("btn_eliminar"), variant="stop")
                        move_up_btn = gr.Button(S.get("btn_subir"), variant="secondary")
                        move_down_btn = gr.Button(S.get("btn_bajar"), variant="secondary")

            # TAB 2: Agregar Lineas
            tab_agregar = gr.Tab(S.get("tab_agregar"), id="tab_agregar")
            with tab_agregar:
                agregar_desc_md = gr.Markdown(S.get("agregar_descripcion"))
                with gr.Row():
                    with gr.Column(scale=1):
                        agregar_ing_titulo_md = gr.Markdown(f"### {S.get('agregar_ingles_titulo')}")
                        en_textarea = gr.Textbox(label="", placeholder=S.get("agregar_ingles_placeholder"), lines=8)
                    with gr.Column(scale=1):
                        agregar_esp_titulo_md = gr.Markdown(f"### {_translation_field_label()}")
                        es_textarea = gr.Textbox(label="", placeholder=S.get("agregar_espanol_placeholder"), lines=8)
                with gr.Row():
                    cat_dropdown = gr.Dropdown(choices=CATEGORIES, value=CATEGORIES[0], label=S.get("agregar_categoria_label"), scale=1)
                    source_input = gr.Textbox(label=S.get("agregar_fuente_label"), value="manual", placeholder=S.get("agregar_fuente_placeholder"), scale=1)
                    add_lines_btn = gr.Button(S.get("btn_agregar_todas"), variant="primary", scale=1)

                gr.Markdown("---")
                single_titulo_md = gr.Markdown(f"### {S.get('agregar_single_titulo')}")
                with gr.Row():
                    single_en = gr.Textbox(label=S.get("single_ingles"), placeholder=S.get("single_ingles_placeholder"), scale=2)
                    single_es = gr.Textbox(label=_translation_field_label(), placeholder=S.get("single_espanol_placeholder"), scale=2)
                    single_cat = gr.Dropdown(choices=CATEGORIES, value=CATEGORIES[0], label=S.get("edit_categoria"), scale=1)
                    single_type = gr.Dropdown(choices=TYPES, value=TYPES[0], label=S.get("edit_tipo"), scale=1)
                    single_source = gr.Textbox(label=S.get("edit_fuente"), value="manual", scale=1)
                    add_single_btn = gr.Button(S.get("btn_agregar"), variant="secondary", scale=1)

            # TAB 3: Vista Previa
            tab_vista = gr.Tab(S.get("tab_vista"), id="tab_vista")
            with tab_vista:
                vista_desc_md = gr.Markdown(S.get("vista_descripcion"))
                preview_html = gr.HTML(value=render_line_preview(state.entries))

            # TAB 4: Archivos en BD
            tab_archivos = gr.Tab(S.get("tab_archivos"), id="tab_archivos")
            with tab_archivos:
                archivos_desc_md = gr.Markdown(S.get("archivos_descripcion"))
                json_list = gr.Textbox(label=S.get("archivos_label"), value="", lines=10, interactive=False)
                refresh_jsons_btn = gr.Button(S.get("btn_actualizar_lista"), variant="secondary")

        # CONECTAR EVENTOS
        new_btn.click(fn=new_glossary, inputs=[filename_input],
                      outputs=[preview_html, stats_html, status_text, search_results,
                               edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden, filename_input])

        load_btn.upload(fn=load_json_file, inputs=[load_btn],
                        outputs=[preview_html, stats_html, status_text, search_results,
                                 edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden, filename_input,
                                 edit_es, single_es, agregar_esp_titulo_md])

        save_btn.click(fn=save_json_file, inputs=[filename_input],
                       outputs=[preview_html, stats_html, status_text, filename_input])

        scan_btn.click(fn=load_all_existing_jsons, inputs=[], outputs=[json_list])

        add_lines_btn.click(fn=add_lines_from_textarea, inputs=[en_textarea, es_textarea, cat_dropdown, source_input],
                            outputs=[preview_html, stats_html, status_text, en_textarea, es_textarea])

        add_single_btn.click(fn=add_single_line, inputs=[single_en, single_es, single_cat, single_type, single_source],
                             outputs=[preview_html, stats_html, status_text, single_en, single_es])

        search_btn.click(fn=search_entries, inputs=[search_input], outputs=[search_results, search_status])
        search_all_btn.click(fn=lambda: search_entries(""), inputs=[], outputs=[search_results, search_status])

        search_results.select(fn=on_table_select, outputs=[edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden])

        save_edit_btn.click(fn=save_edited_entry, inputs=[edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden],
                            outputs=[preview_html, stats_html, status_text, edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden])

        delete_btn.click(fn=delete_selected_entry, inputs=[edit_index_hidden],
                         outputs=[preview_html, stats_html, status_text, edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden])

        move_up_btn.click(fn=lambda idx: move_selected_entry(idx, "up"), inputs=[edit_index_hidden],
                          outputs=[preview_html, stats_html, status_text])
        move_down_btn.click(fn=lambda idx: move_selected_entry(idx, "down"), inputs=[edit_index_hidden],
                            outputs=[preview_html, stats_html, status_text])

        refresh_jsons_btn.click(fn=load_all_existing_jsons, inputs=[], outputs=[json_list])

        # ======== EVENTO - Cambio de idioma ========
        # --- NUEVO: Al cambiar idioma, actualizar toda la UI ---
        # NOTA: load_btn (UploadButton) no se incluye, no soporta gr.update(value=texto)
        lang_outputs = [
            header_html,              # 0: HTML
            filename_input,           # 1: Textbox
            new_btn,                  # 2: Button
            save_btn,                 # 3: Button
            scan_btn,                 # 4: Button
            tab_buscar,               # 5: Tab
            buscar_desc_md,           # 6: Markdown
            search_input,             # 7: Textbox
            search_btn,               # 8: Button
            search_all_btn,           # 9: Button
            search_status,            # 10: Textbox
            search_results,           # 11: Dataframe
            edit_en,                  # 12: Textbox
            edit_es,                  # 13: Textbox
            edit_cat,                 # 14: Dropdown
            edit_type,                # 15: Dropdown
            edit_source,              # 16: Textbox
            acciones_titulo_md,       # 17: Markdown
            save_edit_btn,            # 18: Button
            delete_btn,               # 19: Button
            move_up_btn,              # 20: Button
            move_down_btn,            # 21: Button
            tab_agregar,              # 22: Tab
            agregar_desc_md,          # 23: Markdown
            agregar_ing_titulo_md,    # 24: Markdown
            en_textarea,              # 25: Textbox
            agregar_esp_titulo_md,    # 26: Markdown
            es_textarea,              # 27: Textbox
            cat_dropdown,             # 28: Dropdown
            source_input,             # 29: Textbox
            add_lines_btn,            # 30: Button
            single_titulo_md,         # 31: Markdown
            single_en,                # 32: Textbox
            single_es,                # 33: Textbox
            single_cat,               # 34: Dropdown
            single_type,              # 35: Dropdown
            single_source,            # 36: Textbox
            add_single_btn,           # 37: Button
            tab_vista,                # 38: Tab
            vista_desc_md,            # 39: Markdown
            tab_archivos,             # 40: Tab
            archivos_desc_md,         # 41: Markdown
            json_list,                # 42: Textbox
            refresh_jsons_btn,        # 43: Button
        ]
        lang_dropdown.change(fn=on_lang_change, inputs=[lang_dropdown], outputs=lang_outputs)

    return interface


# ============================================================
# INICIO
# ============================================================
def main():
    print("=" * 60)
    print("EDITOR DE GLOSARIO SKYRIM")
    print("=" * 60)
    print(f"Carpeta BD:    {BD_DIR}")
    print(f"Puerto web:    {GRADIO_PORT}")
    print(f"Gradio version: {gr.__version__}")
    print(f"Strings dir:   {STRINGS_DIR}")
    print(f"Idiomas:       {AVAILABLE_LANGS}")

    print(f"\nAbre en tu navegador: http://localhost:{GRADIO_PORT}")
    print("Para detener, cierra esta ventana o presiona Ctrl+C")
    print("=" * 60)

    try:
        interface = create_interface()
        # Gradio 6.x: theme va en launch(), NO en Blocks()
        launch_kwargs = {
            "server_name": "0.0.0.0",
            "server_port": GRADIO_PORT,
            "share": False,
            "inbrowser": True,
        }

        # Intentar agregar theme (solo si Gradio lo soporta)
        try:
            launch_kwargs["theme"] = gr.themes.Soft(primary_hue="amber")
        except Exception:
            pass  # Si no soporta themes, continuar sin ello

        interface.launch(**launch_kwargs)

    except Exception as e:
        print("\n" + "=" * 60)
        print("[ERROR] No se pudo iniciar el editor")
        print("=" * 60)
        print(f"Error: {e}")
        traceback.print_exc()
        input("Presiona Enter para cerrar...")


if __name__ == "__main__":
    main()

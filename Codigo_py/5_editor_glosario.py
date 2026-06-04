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

    def reset(self):
        self.entries = []
        self.filename = ""
        self.filepath = ""
        self.modified = False
        self.selected_index = -1

    def add_entry(self, english, spanish, category="general", entry_type="", source="manual"):
        entry = {
            "english": english.strip(),
            "spanish": spanish.strip(),
            "category": category or "general",
            "type": entry_type or "",
            "source": source or "manual"
        }
        self.entries.append(entry)
        self.modified = True
        return len(self.entries) - 1

    def update_entry(self, index, english, spanish, category, entry_type, source):
        if 0 <= index < len(self.entries):
            self.entries[index] = {
                "english": english.strip(),
                "spanish": spanish.strip(),
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

    def load_from_json(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            self.entries = data
        elif isinstance(data, dict):
            self.entries = []
            for key, value in data.items():
                if isinstance(value, list):
                    self.entries.extend(value)
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
                query_lower in entry.get("spanish", "").lower() or
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
        es_text = entry.get("spanish", "").replace("<", "&lt;").replace(">", "&gt;")
        cat = entry.get("category", "")
        bg = " background:#3a3a2a;" if i == highlight_idx else ""
        cat_color = CATEGORY_COLORS.get(cat, "#608b4e")
        html_parts.append(f'<div style="display:flex; padding:3px 0; border-bottom:1px solid #333;{bg}">'
                          f'<span style="color:#858585; min-width:40px; text-align:right; padding-right:12px; user-select:none;">{i+1}</span>'
                          f'<span style="color:#9cdcfe; flex:1; padding-right:20px; word-break:break-word;">{en_text}</span>'
                          f'<span style="color:#569cd6; padding:0 8px; user-select:none;">&rarr;</span>'
                          f'<span style="color:#ce9178; flex:1; word-break:break-word;">{es_text}</span>'
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
    if filename and filename.strip():
        safe_name = filename.strip()
        if not safe_name.endswith('.json'):
            safe_name += '.json'
        state.filename = safe_name
        state.filepath = os.path.join(BD_DIR, safe_name)
    return (render_line_preview(state.entries), render_stats(state.entries),
            f"Nuevo glosario: {state.filename or 'sin nombre'}",
            None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "")


def load_json_file(file_obj):
    if file_obj is None:
        return (render_line_preview(state.entries), render_stats(state.entries),
                "No se selecciono ningun archivo", None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "")
    filepath = file_obj.name if hasattr(file_obj, 'name') else str(file_obj)
    try:
        count = state.load_from_json(filepath)
        return (render_line_preview(state.entries), render_stats(state.entries),
                f"Cargado: {state.filename} ({count} entradas)", None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "")
    except Exception as e:
        return (render_line_preview(state.entries), render_stats(state.entries),
                f"Error al cargar: {str(e)}", None, "", "", CATEGORIES[0], TYPES[0], "manual", -1, state.filename or "")


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
        return None, f"No se encontraron resultados para '{query}'"
    table_data = [[idx+1, state.entries[idx].get("english",""), state.entries[idx].get("spanish",""),
                    state.entries[idx].get("category","general"), state.entries[idx].get("type",""),
                    state.entries[idx].get("source","manual")] for idx in indices]
    return table_data, f"Encontradas {len(table_data)} entradas"


def on_table_select(evt: gr.SelectData):
    try:
        row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
        if state.entries and row < len(state.entries):
            entry = state.entries[row]
            state.selected_index = row
            return (entry.get("english",""), entry.get("spanish",""),
                    entry.get("category","general") or CATEGORIES[0],
                    entry.get("type","") or TYPES[0],
                    entry.get("source","manual"), row)
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
    # Gradio 6.x: NO pasar theme ni css a Blocks(), van en launch()
    with gr.Blocks(title="Editor de Glosario Skyrim") as interface:

        gr.HTML('<div style="text-align:center; margin-bottom:5px;"><h1 style="margin:0; color:#d4a017;">Editor de Glosario Skyrim</h1><p style="margin:4px 0 0 0; color:#888; font-size:14px;">Crea y edita archivos JSON con terminologia para el traductor</p></div>')

        with gr.Row():
            filename_input = gr.Textbox(label="Nombre del archivo JSON", placeholder="ej: palabras_agregadas.json", value="", scale=3)
            new_btn = gr.Button("Nuevo", variant="secondary", scale=1)
            load_btn = gr.UploadButton("Cargar JSON", file_types=[".json"], variant="secondary", scale=1)
            save_btn = gr.Button("Guardar JSON", variant="primary", scale=1)
            scan_btn = gr.Button("Buscar JSONs en BD", variant="secondary", scale=1)

        status_text = gr.HTML(value="<p style='color:#888;'>Listo para crear o cargar un glosario</p>")
        stats_html = gr.HTML(value=render_stats(state.entries))

        with gr.Tabs():

            # TAB 1: Agregar Lineas
            with gr.Tab("Agregar Lineas"):
                gr.Markdown("**Modo de uso:** Cada linea se convierte en una entrada. Las lineas se emparejan por numero (1 con 1, 2 con 2, etc).")
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Texto Original (Ingles)")
                        en_textarea = gr.Textbox(label="", placeholder="Pega aqui las lineas en ingles...\n\nCada linea = una entrada", lines=10)
                    with gr.Column(scale=1):
                        gr.Markdown("### Texto Traducido (Espanol)")
                        es_textarea = gr.Textbox(label="", placeholder="Pega aqui las traducciones...\n\nCada linea = una entrada", lines=10)
                with gr.Row():
                    cat_dropdown = gr.Dropdown(choices=CATEGORIES, value=CATEGORIES[0], label="Categoria", scale=1)
                    source_input = gr.Textbox(label="Fuente (source)", value="manual", placeholder="ej: manual, mod_xxx", scale=1)
                    add_lines_btn = gr.Button("Agregar todas las lineas", variant="primary", scale=1)

                gr.Markdown("---")
                gr.Markdown("### Agregar una sola entrada detallada")
                with gr.Row():
                    single_en = gr.Textbox(label="Ingles", placeholder="Texto en ingles", scale=2)
                    single_es = gr.Textbox(label="Espanol", placeholder="Traduccion al espanol", scale=2)
                    single_cat = gr.Dropdown(choices=CATEGORIES, value=CATEGORIES[0], label="Categoria", scale=1)
                    single_type = gr.Dropdown(choices=TYPES, value=TYPES[0], label="Tipo", scale=1)
                    single_source = gr.Textbox(label="Fuente", value="manual", scale=1)
                    add_single_btn = gr.Button("Agregar", variant="secondary", scale=1)

            # TAB 2: Vista Previa
            with gr.Tab("Vista Previa"):
                gr.Markdown("**Vista previa** con numeros de linea, como en ESP Translate.")
                preview_html = gr.HTML(value=render_line_preview(state.entries))

            # TAB 3: Buscar y Editar
            with gr.Tab("Buscar y Editar"):
                gr.Markdown("**Busca y edita entradas existentes.** Haz clic en una fila para editarla.")
                with gr.Row():
                    search_input = gr.Textbox(label="Buscar", placeholder="Buscar en ingles, espanol o categoria...", scale=4)
                    search_btn = gr.Button("Buscar", variant="primary", scale=1)
                    search_all_btn = gr.Button("Ver Todas", variant="secondary", scale=1)

                search_status = gr.Textbox(label="Resultado", value="", interactive=False)
                search_results = gr.Dataframe(
                    headers=["#", "Ingles", "Espanol", "Categoria", "Tipo", "Fuente"],
                    label="Entradas encontradas (clic para editar)",
                    interactive=False, wrap=True
                )

                gr.Markdown("---")
                gr.Markdown("### Editar entrada seleccionada")
                edit_index_hidden = gr.Number(value=-1, visible=False, precision=0)

                with gr.Row():
                    edit_en = gr.Textbox(label="Ingles", placeholder="Selecciona una entrada de la tabla...", scale=3)
                    edit_es = gr.Textbox(label="Espanol", placeholder="...", scale=3)
                with gr.Row():
                    edit_cat = gr.Dropdown(choices=CATEGORIES, value=CATEGORIES[0], label="Categoria", scale=1)
                    edit_type = gr.Dropdown(choices=TYPES, value=TYPES[0], label="Tipo", scale=1)
                    edit_source = gr.Textbox(label="Fuente", value="manual", scale=1)
                with gr.Row():
                    save_edit_btn = gr.Button("Guardar Cambios", variant="primary", scale=1)
                    delete_btn = gr.Button("Eliminar", variant="stop", scale=1)
                    move_up_btn = gr.Button("Subir", variant="secondary", scale=1)
                    move_down_btn = gr.Button("Bajar", variant="secondary", scale=1)

            # TAB 4: Archivos en BD
            with gr.Tab("Archivos en BD"):
                gr.Markdown("**Archivos JSON en la carpeta BD** que el actualizador leeria para agregar terminos a ChromaDB.")
                json_list = gr.Textbox(label="Archivos JSON en BD", value="", lines=10, interactive=False)
                refresh_jsons_btn = gr.Button("Actualizar lista", variant="secondary")

        # CONECTAR EVENTOS
        new_btn.click(fn=new_glossary, inputs=[filename_input],
                      outputs=[preview_html, stats_html, status_text, search_results,
                               edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden, filename_input])

        load_btn.upload(fn=load_json_file, inputs=[load_btn],
                        outputs=[preview_html, stats_html, status_text, search_results,
                                 edit_en, edit_es, edit_cat, edit_type, edit_source, edit_index_hidden, filename_input])

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

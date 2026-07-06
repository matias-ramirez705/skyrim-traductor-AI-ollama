"""
=====================================================
LIMPIEZA DE GLOSARIO - Elimina entradas corruptas
del JSON existente sin necesidad de re-procesar
los archivos .strings binarios.
(SOPORTE MULTILENGUAJE)
=====================================================

Problema: El glosario tiene entradas corruptas como:
  {"english": "w", "spanish": "", ...}

Este script:
1. Detecta los glosarios disponibles en BD/
2. Permite seleccionar cual limpiar
3. Elimina entradas corruptas, vacias y duplicadas
4. Guarda el JSON limpio

USO: python limpiar_glosario.py
"""

import os
import sys
import json
import glob

# ============================================================
# CONFIGURACION
# ============================================================
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(_SCRIPT_DIR, "BD")):
    BASE_DIR = _SCRIPT_DIR
elif os.path.exists(os.path.join(_SCRIPT_DIR, "..", "BD")):
    BASE_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
else:
    BASE_DIR = _SCRIPT_DIR
BD_DIR = os.path.join(BASE_DIR, "BD")


def _detect_translation_field(entries):
    """Detecta el campo de traduccion en las entradas."""
    if not entries:
        return "spanish"
    known = {"english", "category", "type", "source"}
    for key in entries[0].keys():
        if key not in known:
            return key
    return "spanish"


def detect_glossary_files():
    """Detecta todos los archivos skyrim_glossary_en_*.json en BD/."""
    pattern = os.path.join(BD_DIR, "skyrim_glossary_en_*.json")
    files = glob.glob(pattern)
    glossaries = []
    for filepath in sorted(files):
        filename = os.path.basename(filepath)
        prefix = "skyrim_glossary_en_"
        if filename.startswith(prefix) and filename.endswith(".json"):
            lang_code = filename[len(prefix):-5]
        else:
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                entry_count = len(data)
                tr_field = _detect_translation_field(data)
            elif isinstance(data, dict) and "entries" in data:
                entries = data["entries"]
                entry_count = len(entries)
                tr_field = data.get("metadata", {}).get("translation_field",
                    _detect_translation_field(entries))
            else:
                continue
        except Exception:
            continue
        glossaries.append({
            "filepath": filepath,
            "filename": filename,
            "lang_code": lang_code,
            "translation_field": tr_field,
            "entry_count": entry_count,
        })
    return glossaries


def select_glossary(glossaries):
    """Muestra glosarios y permite seleccionar uno."""
    if not glossaries:
        return None
    if len(glossaries) == 1:
        g = glossaries[0]
        print(f"\nSolo se encontro un glosario: {g['filename']}")
        return g

    print(f"\n{'=' * 60}")
    print("GLOSARIOS DISPONIBLES:")
    print(f"{'=' * 60}")
    for i, g in enumerate(glossaries, 1):
        print(f"  {i}. {g['filename']} ({g['entry_count']} entradas, campo: \"{g['translation_field']}\")")

    while True:
        try:
            choice = input(f"\nSelecciona [1-{len(glossaries)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(glossaries):
                return glossaries[idx]
            print("Numero fuera de rango.")
        except ValueError:
            print("Ingresa un numero valido.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperacion cancelada.")
            return None


def main():
    print("=" * 60)
    print("LIMPIEZA DE GLOSARIO - MULTILENGUAJE")
    print("=" * 60)

    if not os.path.exists(BD_DIR):
        print(f"[ERROR] No se encontro la carpeta BD/: {BD_DIR}")
        sys.exit(1)

    # Detectar glosarios
    glossaries = detect_glossary_files()
    if not glossaries:
        print(f"\n[ERROR] No se encontraron archivos skyrim_glossary_en_*.json en BD/")
        sys.exit(1)

    # Seleccionar glosario
    selected = select_glossary(glossaries)
    if not selected:
        sys.exit(0)

    GLOSSARY_FILE = selected["filepath"]
    BACKUP_FILE = GLOSSARY_FILE.replace(".json", "_backup.json")
    lang_field = selected["translation_field"]

    print(f"\nLimpiando: {selected['filename']}")
    print(f"  Campo de traduccion: \"{lang_field}\"")

    # Cargar glosario
    with open(GLOSSARY_FILE, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    # Si tiene formato con metadata, extraer entries
    if isinstance(entries, dict) and "entries" in entries:
        entries = entries["entries"]

    print(f"Entradas originales: {len(entries)}")

    # Hacer backup
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"Backup guardado en: {os.path.basename(BACKUP_FILE)}")

    # Estadisticas de problemas
    empty_tr = 0
    short_en = 0

    print("\nAnalizando entradas...")

    for entry in entries:
        en = entry.get("english", "").strip()
        tr = entry.get(lang_field, "").strip()
        if not tr:
            empty_tr += 1
        if len(en) <= 2:
            short_en += 1

    print(f"  Entradas sin traduccion ({lang_field} vacio): {empty_tr}")
    print(f"  Entradas con ingles muy corto (1-2 chars): {short_en}")

    # Limpiar
    clean = []
    removed_empty = 0
    removed_short = 0
    removed_duplicate = 0
    seen_en = set()

    for entry in entries:
        en = entry.get("english", "").strip()
        tr = entry.get(lang_field, "").strip()

        if not tr:
            removed_empty += 1
            continue

        if len(en) <= 1:
            removed_short += 1
            continue

        en_key = en.lower()
        if en_key in seen_en:
            removed_duplicate += 1
            continue

        seen_en.add(en_key)
        clean.append(entry)

    print(f"\nResultado de la limpieza:")
    print(f"  Removidas sin traduccion: {removed_empty}")
    print(f"  Removidas ingles corto:   {removed_short}")
    print(f"  Removidas duplicadas:     {removed_duplicate}")
    print(f"  Total removidas:          {removed_empty + removed_short + removed_duplicate}")
    print(f"  Entradas limpias:         {len(clean)}")

    # Guardar
    with open(GLOSSARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    print(f"\nGlosario limpio guardado en: {selected['filename']}")

    # Verificar terminos clave
    print("\n--- Verificacion de terminos clave ---")
    test_terms = ["whiterun", "windhelm", "solitude", "riften",
                  "markarth", "stormcloaks", "imperial", "dragonborn"]

    en_lookup = {}
    for e in clean:
        en_lookup[e["english"].lower()] = e

    for term in test_terms:
        if term in en_lookup:
            e = en_lookup[term]
            tr_val = e.get(lang_field, "???")
            print(f"  OK: {e['english']} -> {tr_val}")
        else:
            found = [e for e in clean if term in e["english"].lower()]
            if found:
                print(f"  PARCIAL '{term}' en {len(found)} entradas:")
                for e in found[:3]:
                    tr_val = e.get(lang_field, "???")
                    print(f"    {e['english']} -> {tr_val}")
            else:
                print(f"  NO ENCONTRADO: '{term}'")

    # Estadisticas por categoria
    print("\n--- Estadisticas por categoria ---")
    categories = {}
    for entry in clean:
        cat = entry.get("category", "sin_categoria")
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    print(f"\nListo! Ahora ejecuta: 3_iniciar_glosario.bat")


if __name__ == "__main__":
    main()

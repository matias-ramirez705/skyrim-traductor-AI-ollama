"""
=====================================================
LIMPIEZA DE GLOSARIO - Elimina entradas corruptas
del JSON existente sin necesidad de re-procesar
los archivos .strings binarios.
=====================================================

Problema: El glosario tiene entradas corruptas como:
  {"english": "w", "spanish": "", ...}

Este script:
1. Elimina entradas donde english tiene 1-2 caracteres y spanish esta vacio
2. Elimina entradas donde spanish esta vacio
3. Elimina duplicados
4. Guarda el JSON limpio

USO: python limpiar_glosario.py
"""

import os
import sys
import json

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
GLOSSARY_FILE = os.path.join(BD_DIR, "skyrim_glossary_en_es.json")
BACKUP_FILE = os.path.join(BD_DIR, "skyrim_glossary_en_es_backup.json")


def main():
    print("=" * 60)
    print("LIMPIEZA DE GLOSARIO")
    print("=" * 60)

    # Cargar glosario
    if not os.path.exists(GLOSSARY_FILE):
        print(f"[ERROR] No se encontro: {GLOSSARY_FILE}")
        sys.exit(1)

    with open(GLOSSARY_FILE, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Entradas originales: {len(entries)}")

    # Hacer backup
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"Backup guardado en: {BACKUP_FILE}")

    # Estadisticas de problemas
    empty_es = 0
    short_en = 0
    total_problems = 0

    print("\nAnalizando entradas...")

    for entry in entries:
        en = entry.get("english", "").strip()
        es = entry.get("spanish", "").strip()

        if not es:
            empty_es += 1
        if len(en) <= 2:
            short_en += 1

    print(f"  Entradas sin traduccion (spanish vacio): {empty_es}")
    print(f"  Entradas con ingles muy corto (1-2 chars): {short_en}")

    # Limpiar
    clean = []
    removed_empty = 0
    removed_short = 0
    removed_duplicate = 0

    seen_en = set()

    for entry in entries:
        en = entry.get("english", "").strip()
        es = entry.get("spanish", "").strip()

        # Saltar sin traduccion
        if not es:
            removed_empty += 1
            continue

        # Saltar ingles muy corto (probablemente corrupto)
        if len(en) <= 1:
            removed_short += 1
            continue

        # Saltar duplicados (mismo texto en ingles)
        en_key = en.lower()
        if en_key in seen_en:
            # Si el duplicado tiene mejor traduccion, reemplazar
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

    print(f"\nGlosario limpio guardado en: {GLOSSARY_FILE}")

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
            print(f"  OK: {e['english']} -> {e['spanish']}")
        else:
            # Buscar parcial
            found = [e for e in clean if term in e["english"].lower()]
            if found:
                print(f"  PARCIAL '{term}' en {len(found)} entradas:")
                for e in found[:3]:
                    print(f"    {e['english']} -> {e['spanish']}")
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

    print("\nListo! Ahora ejecuta: 3_iniciar_glosario.bat")


if __name__ == "__main__":
    main()

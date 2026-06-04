"""
=====================================================
CREADOR DE GLOSARIO - Parsea archivos .strings de
Skyrim y crea un JSON con pares EN->ES
=====================================================

Lee los archivos binarios .strings / .dlstrings / .ilstrings
del mod "Multiple Languages Strings Unified Central SSE-AE"
y crea un glosario JSON con terminologia ingles->espanol.

FORMATO BINARIO DE BETHESDA (.strings):
---------------------------------------
1. Header (8 bytes):
   - numEntries (uint32 LE): cantidad de entradas
   - dataSize   (uint32 LE): tamaño del bloque de datos

2. Directorio (numEntries * 8 bytes):
   - stringID (uint32 LE): ID del string
   - offset   (uint32 LE): offset RELATIVO al inicio del bloque de datos

3. Bloque de datos (dataSize bytes):
   - Cadenas null-terminated UTF-8 en los offsets indicados

Los archivos vienen en pares: skyrim_english.strings + skyrim_spanish.strings
Se emparejan por stringID para obtener la traduccion.

USO: python crear_glosario.py
"""

import os
import sys
import struct
import json
import unicodedata

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

# Carpetas con los strings
EN_BASE = os.path.join(BD_DIR, "0 - English Original Strings", "strings")
ES_BASE = os.path.join(BD_DIR, "0 - Spanish Original Strings", "strings")
EN_DLC  = os.path.join(BD_DIR, "1 - English DLC Strings", "strings")
ES_DLC  = os.path.join(BD_DIR, "1 - Spanish DLC Strings", "strings")

OUTPUT_FILE = os.path.join(BD_DIR, "skyrim_glossary_en_es.json")

# Nombres de archivo a buscar (sin el sufijo _english/_spanish)
STRING_FILES = [
    ("skyrim",    "skyrim_esm"),
    ("dawnguard", "dawnguard_esm"),
    ("dragonborn","dragonborn_esm"),
    ("hearthfires","hearthfires_esm"),
]


# ============================================================
# PARSER BINARIO
# ============================================================

def parse_strings_file(filepath):
    """
    Parsea un archivo .strings, .dlstrings o .ilstrings de Bethesda.
    Devuelve un diccionario: {stringID: texto}

    Formato binario:
    - Header: uint32 numEntries, uint32 dataSize
    - Directorio: numEntries * (uint32 stringID, uint32 offset)
    - Data block: dataSize bytes con strings null-terminated UTF-8
      Los offsets son RELATIVOS al inicio del data block
    """
    if not os.path.exists(filepath):
        print(f"  [AVISO] No existe: {filepath}")
        return {}

    entries = {}

    with open(filepath, 'rb') as f:
        data = f.read()

    if len(data) < 8:
        print(f"  [AVISO] Archivo demasiado pequeño: {filepath}")
        return {}

    # 1. Leer header
    num_entries, data_size = struct.unpack_from('<II', data, 0)

    # Calcular donde empieza el data block
    # header (8 bytes) + directorio (num_entries * 8 bytes)
    directory_size = num_entries * 8
    data_block_start = 8 + directory_size

    # Verificar que el archivo tiene el tamaño correcto
    expected_size = data_block_start + data_size
    if len(data) < expected_size:
        print(f"  [AVISO] Tamaño incorrecto en {os.path.basename(filepath)}: "
              f"esperado {expected_size}, tiene {len(data)}")
        # Intentar igual, quizas el dataSize es aproximado

    # 2. Leer directorio y extraer strings
    for i in range(num_entries):
        dir_offset = 8 + (i * 8)

        if dir_offset + 8 > len(data):
            break

        string_id, string_offset = struct.unpack_from('<II', data, dir_offset)

        # El string_offset es RELATIVO al data block
        abs_offset = data_block_start + string_offset

        # Leer string null-terminated desde el data block
        if abs_offset >= len(data):
            continue

        # Buscar el byte null (0x00) que termina el string
        end_offset = abs_offset
        while end_offset < len(data) and data[end_offset] != 0:
            end_offset += 1

        # Extraer los bytes del string y decodificar como UTF-8
        string_bytes = data[abs_offset:end_offset]

        try:
            text = string_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # Intentar con latin-1 como fallback
            try:
                text = string_bytes.decode('latin-1')
            except:
                text = ""

        # Limpiar texto: remover caracteres de control, normalizar
        text = clean_text(text)

        if text:
            entries[string_id] = text

    return entries


def clean_text(text):
    """Limpia un texto: remueve caracteres de control, espacios extra, etc."""
    if not text:
        return ""

    # Remover caracteres de control excepto salto de linea y tab
    cleaned = ""
    for ch in text:
        if ch in ('\n', '\r', '\t'):
            cleaned += ch
        elif unicodedata.category(ch).startswith('C'):
            continue  # Caracter de control, skip
        else:
            cleaned += ch

    # Remover espacios multiples
    cleaned = ' '.join(cleaned.split())

    return cleaned.strip()


# ============================================================
# EMPAREJAR Y CLASIFICAR
# ============================================================

def classify_entry(english, spanish, source):
    """Clasifica una entrada por categoria y tipo"""
    en_lower = english.lower()
    es_lower = spanish.lower()

    # Detectar categoria
    category = "general"
    entry_type = ""

    # Lugares: contiene indicadores de ubicacion
    location_words = ["hold", "city", "town", "village", "keep", "castle",
                      "fort", "cave", "mine", "camp", "sanctuary", "temple",
                      "hall", "manor", "farm", "mill", "inn", "barracks",
                      "dungeon", "ruins", "barrow", "shrine", "tower", "sewer"]
    if any(w in en_lower for w in location_words):
        category = "lugar"

    # NPCs: patron de nombre propio
    npc_indicators = ["jarl", "thane", "court wizard", "housecarl",
                      "steward", "priest", "blacksmith", "merchant",
                      "guard", "soldier", "commander", "general",
                      "arch-mage", "master"]
    if any(w in en_lower for w in npc_indicators):
        category = "npc"

    # Magia
    magic_words = ["spell", "enchant", "conjuration", "destruction",
                   "restoration", "illusion", "alteration", "mage",
                   "magic", "magicka", "shout", "thu'um", "dragon shout",
                   "word of power", "scroll"]
    if any(w in en_lower for w in magic_words):
        category = "magia"

    # Armas
    weapon_words = ["sword", "axe", "bow", "dagger", "mace", "warhammer",
                    "greatsword", "battleaxe", "staff", "arrow", "blade"]
    if any(w in en_lower for w in weapon_words):
        category = "arma"

    # Armadura
    armor_words = ["armor", "armour", "shield", "helmet", "gauntlet",
                   "boots", "cuirass", "greaves", "pauldron"]
    if any(w in en_lower for w in armor_words):
        category = "armadura"

    # Criaturas
    creature_words = ["dragon", "draugr", "vampire", "werewolf", "spriggan",
                      "hagraven", "giant", "mammoth", "sabre cat", "bear",
                      "wolf", "spider", "troll", "skeleton", "wispmother",
                      "falmer", "draugr", "daedra", "atronach"]
    if any(w in en_lower for w in creature_words):
        category = "criatura"

    # Facciones
    faction_words = ["stormcloak", "imperial", "thieves guild", "dark brotherhood",
                     "companions", "college of", "bard", "blades", "greybeards",
                     "thalmor", " legion"]
    if any(w in en_lower for w in faction_words):
        category = "faccion"

    # Misiones
    quest_words = ["quest", "mission", "journey", "task", "errand"]
    if any(w in en_lower for w in quest_words):
        category = "mision"

    # Dialogo: si es una frase larga con verbos comunes
    dialogue_verbs = ["i need", "i want", "i'm looking", "can you",
                      "would you", "have you", "do you", "what is",
                      "where is", "how do", "tell me", "let me",
                      "i don't", "i won't", "you must", "you should"]
    if any(w in en_lower for w in dialogue_verbs):
        category = "dialogo"
        entry_type = "dialogo"

    # Si es solo 1-3 palabras, probablemente un nombre
    word_count = len(english.split())
    if word_count <= 2 and category == "general":
        entry_type = "nombre"

    # Descripciones: frases mas largas
    if word_count > 8 and category == "general":
        category = "descripcion"
        entry_type = "descripcion"

    return category, entry_type


def match_entries(en_entries, es_entries, source_name):
    """
    Empareja entradas inglesas con espanolas por stringID.
    Devuelve una lista de diccionarios con los pares.
    """
    pairs = []
    matched = 0
    no_match = 0

    for string_id, en_text in en_entries.items():
        if not en_text.strip():
            continue

        es_text = es_entries.get(string_id, "")

        # Si no hay traduccion, saltar
        if not es_text.strip():
            no_match += 1
            continue

        # Si ingles y espanol son identicos, probablemente no se traduce
        # (pero lo incluimos igual, puede ser nombre propio)
        category, entry_type = classify_entry(en_text, es_text, source_name)

        pairs.append({
            "english": en_text.strip(),
            "spanish": es_text.strip(),
            "category": category,
            "type": entry_type,
            "source": source_name,
        })
        matched += 1

    return pairs, matched, no_match


# ============================================================
# PROCESAR ARCHIVOS
# ============================================================

def process_strings_file_pair(en_dir, es_dir, base_name, source_name):
    """Procesa un par de archivos .strings (ingles + espanol)"""
    results = []

    # Los 3 tipos de archivos: .strings, .dlstrings, .ilstrings
    suffixes = [".strings", ".dlstrings", ".ilstrings"]
    suffix_names = ["strings", "dlstrings", "ilstrings"]

    for suffix, suffix_name in zip(suffixes, suffix_names):
        # Nombres de archivo posibles
        en_paths = [
            os.path.join(en_dir, f"{base_name}_english{suffix}"),
            os.path.join(en_dir, f"{base_name}{suffix}"),
        ]
        es_paths = [
            os.path.join(es_dir, f"{base_name}_spanish{suffix}"),
            os.path.join(es_dir, f"{base_name}_espanol{suffix}"),
            os.path.join(es_dir, f"{base_name}{suffix}"),
        ]

        # Buscar archivos que existan
        en_file = None
        es_file = None

        for p in en_paths:
            if os.path.exists(p):
                en_file = p
                break

        for p in es_paths:
            if os.path.exists(p):
                es_file = p
                break

        if not en_file or not es_file:
            continue

        print(f"  Procesando: {os.path.basename(en_file)} + {os.path.basename(es_file)}")

        # Parsear ambos archivos
        en_entries = parse_strings_file(en_file)
        es_entries = parse_strings_file(es_file)

        print(f"    EN: {len(en_entries)} entradas | ES: {len(es_entries)} entradas")

        # Emparejar
        full_source = f"{source_name}_{suffix_name}"
        pairs, matched, no_match = match_entries(en_entries, es_entries, full_source)
        results.extend(pairs)

        print(f"    Pares encontrados: {matched} | Sin traduccion: {no_match}")

    return results


def main():
    print("=" * 60)
    print("CREADOR DE GLOSARIO SKYRIM")
    print("=" * 60)

    all_entries = []

    # Procesar strings del juego base
    if os.path.exists(EN_BASE) and os.path.exists(ES_BASE):
        print("\n--- Strings del juego base ---")
        for base_name, source_name in STRING_FILES:
            print(f"\nBuscando: {base_name}")
            pairs = process_strings_file_pair(EN_BASE, ES_BASE, base_name, source_name)
            all_entries.extend(pairs)
    else:
        print(f"\n[AVISO] No se encontraron carpetas de strings base")
        print(f"  EN: {EN_BASE}")
        print(f"  ES: {ES_BASE}")

    # Procesar strings de DLC
    if os.path.exists(EN_DLC) and os.path.exists(ES_DLC):
        print("\n--- Strings de DLC ---")
        for base_name, source_name in STRING_FILES:
            print(f"\nBuscando: {base_name}")
            pairs = process_strings_file_pair(EN_DLC, ES_DLC, base_name, f"{source_name}_dlc")
            all_entries.extend(pairs)
    else:
        print(f"\n[AVISO] No se encontraron carpetas de DLC strings")

    # Si no hay entradas, buscar todos los .strings en las carpetas
    if not all_entries:
        print("\n[AVISO] No se encontraron entradas con los nombres esperados.")
        print("Buscando todos los archivos .strings disponibles...")
        all_entries = scan_all_strings()

    if not all_entries:
        print("\n[ERROR] No se encontraron archivos .strings para procesar.")
        print("Asegurate de que los archivos esten en las carpetas correctas.")
        sys.exit(1)

    # Eliminar duplicados (mismo texto en ingles)
    print(f"\nTotal antes de deduplicar: {len(all_entries)}")
    seen = {}
    unique_entries = []
    for entry in all_entries:
        key = entry["english"].lower().strip()
        if key not in seen:
            seen[key] = entry
            unique_entries.append(entry)
        else:
            # Si la nueva entrada tiene mejor traduccion (no vacia), reemplazar
            existing = seen[key]
            if not existing.get("spanish", "").strip() and entry.get("spanish", "").strip():
                idx = unique_entries.index(existing)
                unique_entries[idx] = entry
                seen[key] = entry

    all_entries = unique_entries
    print(f"Total despues de deduplicar: {len(all_entries)}")

    # Eliminar entradas sospechosas (texto muy corto o vacio)
    clean_entries = []
    removed = 0
    for entry in all_entries:
        en = entry.get("english", "").strip()
        es = entry.get("spanish", "").strip()

        # Saltar entradas vacias o con solo 1 caracter
        if len(en) <= 1:
            removed += 1
            continue

        # Saltar si no hay traduccion
        if not es:
            removed += 1
            continue

        clean_entries.append(entry)

    if removed > 0:
        print(f"Entradas removidas (vacias o corruptas): {removed}")
        print(f"Total limpio: {len(clean_entries)}")

    all_entries = clean_entries

    # Guardar JSON
    print(f"\nGuardando glosario en: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"Glosario guardado: {len(all_entries)} entradas")

    # Estadisticas
    print("\n--- Estadisticas por categoria ---")
    categories = {}
    for entry in all_entries:
        cat = entry.get("category", "sin_categoria")
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Verificar entradas importantes
    print("\n--- Verificacion de terminos clave ---")
    test_terms = ["whiterun", "stormcloaks", "windhelm", "solitude",
                  "imperial legion", "dragonborn", "thu'um", "daedra"]
    en_lookup = {e["english"].lower(): e for e in all_entries}

    for term in test_terms:
        if term in en_lookup:
            e = en_lookup[term]
            print(f"  OK: {e['english']} -> {e['spanish']}")
        else:
            # Buscar parcial
            found = [e for e in all_entries if term in e["english"].lower()]
            if found:
                print(f"  PARCIAL: '{term}' encontrado en {len(found)} entradas")
                for e in found[:3]:
                    print(f"    {e['english']} -> {e['spanish']}")
            else:
                print(f"  NO ENCONTRADO: '{term}'")

    print("\nListo! Ahora ejecuta: 3_iniciar_glosario.bat")


def scan_all_strings():
    """Escanea todas las carpetas buscando archivos .strings"""
    all_entries = []

    for en_dir, es_dir in [(EN_BASE, ES_BASE), (EN_DLC, ES_DLC)]:
        if not os.path.exists(en_dir) or not os.path.exists(es_dir):
            continue

        # Listar todos los archivos .strings en la carpeta inglesa
        for filename in os.listdir(en_dir):
            if not filename.endswith('.strings'):
                continue

            # Construir el nombre base: remover _english y la extension
            base = filename.replace('.strings', '').replace('.dlstrings', '').replace('.ilstrings', '')
            base = base.replace('_english', '').replace('_English', '')

            # Buscar el archivo espanol correspondiente
            es_filename = filename.replace('_english', '_spanish').replace('_English', '_Spanish')

            es_file = os.path.join(es_dir, es_filename)
            en_file = os.path.join(en_dir, filename)

            if not os.path.exists(es_file):
                # Intentar otras variaciones
                alt_names = [
                    filename.replace('_english', '_espanol'),
                    filename.replace('_english', '_Spanish'),
                    filename.replace('_English', '_spanish'),
                    filename,
                ]
                for alt in alt_names:
                    alt_path = os.path.join(es_dir, alt)
                    if os.path.exists(alt_path):
                        es_file = alt_path
                        break

            if os.path.exists(es_file):
                print(f"  Encontrado par: {filename}")
                en_entries = parse_strings_file(en_file)
                es_entries = parse_strings_file(es_file)

                source = base.replace('_', ' ')
                pairs, matched, no_match = match_entries(en_entries, es_entries, source)
                all_entries.extend(pairs)
                print(f"    EN: {len(en_entries)} | ES: {len(es_entries)} | Pares: {matched}")

    return all_entries


if __name__ == "__main__":
    main()

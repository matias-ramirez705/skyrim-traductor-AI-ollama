"""
=====================================================
CREADOR DE GLOSARIO - Parsea archivos .strings de
Skyrim y crea un JSON con pares EN->[IDIOMA DESTINO]
=====================================================

Lee los archivos binarios .strings / .dlstrings / .ilstrings
del mod "Multiple Languages Strings Unified Central SSE-AE"
y crea un glosario JSON con terminologia ingles->idioma_destino.

SOPORTE MULTILENGUAJE:
----------------------
- Las carpetas de English siempre son las mismas (source fijo)
- Escanea la carpeta BD/ y lista las carpetas disponibles
- El usuario selecciona la carpeta de strings base (0 - *) y DLC (1 - *)
- El usuario indica el nombre del campo de traduccion (ej: "spanish")
- El usuario indica el codigo para el archivo (ej: "es")
- El archivo de salida se nombra: skyrim_glossary_en_[codigo].json

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

Los archivos vienen en pares: skyrim_esm_english.strings + skyrim_esm_spanish.strings
Se emparejan por stringID para obtener la traduccion.

USO: python 0_crear_glosario.py
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

# Carpetas con los strings en ingles (siempre las mismas, son el source fijo)
EN_BASE = os.path.join(BD_DIR, "0 - English Original Strings", "strings")
EN_DLC  = os.path.join(BD_DIR, "1 - English DLC Strings", "strings")

# ============================================================
# REFERENCIA DE IDIOMAS DE SKYRIM
# ============================================================
# No es obligatorio tener estos idiomas - es una referencia para los
# sufijos de archivo .strings que usa cada idioma.
# Cuando el usuario selecciona una carpeta, se intenta detectar
# automaticamente el idioma para usar los sufijos correctos.
# Si no se detecta, se usa el nombre de la carpeta como sufijo.
#
# Formato: codigo -> { name, folder_keywords, file_suffixes }
#   - name: nombre completo del idioma
#   - folder_keywords: palabras clave que pueden aparecer en el nombre
#     de la carpeta para detectar automaticamente el idioma
#   - file_suffixes: sufijos posibles en los nombres de archivo .strings
#     (orden de prioridad: se usa el primero que se encuentre)
LANG_REFERENCE = {
    "es": {
        "name": "Spanish",
        "folder_keywords": ["spanish", "espanol"],
        "file_suffixes": ["_spanish", "_espanol", "_Spanish", "_Espanol"],
    },
    "ru": {
        "name": "Russian",
        "folder_keywords": ["russian"],
        "file_suffixes": ["_russian", "_Russian"],
    },
    "pt_br": {
        "name": "Portuguese Brazil",
        "folder_keywords": ["portuguese", "brazil", "ptbr", "pt-br", "brazilian"],
        "file_suffixes": ["_brazilian", "_portuguese", "_Brazilian", "_Portuguese"],
    },
    "hu": {
        "name": "Hungarian",
        "folder_keywords": ["hungarian"],
        "file_suffixes": ["_hungarian", "_Hungarian"],
    },
    "zh_cn": {
        "name": "Chinese Simplified",
        "folder_keywords": ["chinese simplified", "chinese_simplified", "simplified"],
        "file_suffixes": ["_chinese", "_chinese_simplified", "_Chinese", "_Chinese_Simplified"],
    },
    "zh_tw": {
        "name": "Chinese Traditional",
        "folder_keywords": ["chinese traditional", "chinese_traditional", "traditional"],
        "file_suffixes": ["_chinese_traditional", "_t_chinese", "_Chinese_Traditional"],
    },
    "cs": {
        "name": "Czech",
        "folder_keywords": ["czech"],
        "file_suffixes": ["_czech", "_Czech"],
    },
    "uk": {
        "name": "Ukrainian",
        "folder_keywords": ["ukrainian"],
        "file_suffixes": ["_ukrainian", "_Ukrainian"],
    },
    "ko": {
        "name": "Korean",
        "folder_keywords": ["korean"],
        "file_suffixes": ["_korean", "_Korean"],
    },
    "tr": {
        "name": "Turkish",
        "folder_keywords": ["turkish", "turkey"],
        "file_suffixes": ["_turkish", "_Turkish"],
    },
    "pl": {
        "name": "Polish",
        "folder_keywords": ["polish"],
        "file_suffixes": ["_polish", "_Polish"],
    },
    "ja": {
        "name": "Japanese",
        "folder_keywords": ["japanese"],
        "file_suffixes": ["_japanese", "_Japanese"],
    },
    "it": {
        "name": "Italian",
        "folder_keywords": ["italian"],
        "file_suffixes": ["_italian", "_Italian"],
    },
    "de": {
        "name": "German",
        "folder_keywords": ["german"],
        "file_suffixes": ["_german", "_German"],
    },
    "fr": {
        "name": "French",
        "folder_keywords": ["french"],
        "file_suffixes": ["_french", "_French"],
    },
}

# Nombres de archivo a buscar (sin el sufijo _english/_spanish)
STRING_FILES = [
    ("skyrim",    "skyrim_esm"),
    ("dawnguard", "dawnguard_esm"),
    ("dragonborn","dragonborn_esm"),
    ("hearthfires","hearthfires_esm"),
]


# ============================================================
# DETECCION DE CARPETAS DISPONIBLES
# ============================================================

def scan_bd_folders():
    """
    Escanea la carpeta BD/ y clasifica las subcarpetas en:
    - base_folders: carpetas que empiezan con "0 -" (juego base)
    - dlc_folders: carpetas que empiezan con "1 -" (DLC)
    - other: otras carpetas
    Retorna: (base_folders, dlc_folders)
    """
    base_folders = []
    dlc_folders = []

    if not os.path.exists(BD_DIR):
        return base_folders, dlc_folders

    for name in sorted(os.listdir(BD_DIR)):
        full_path = os.path.join(BD_DIR, name)
        if not os.path.isdir(full_path):
            continue

        if name.startswith("0 -"):
            base_folders.append(name)
        elif name.startswith("1 -"):
            dlc_folders.append(name)

    return base_folders, dlc_folders


def select_folder_from_list(folders, folder_type):
    """
    Muestra una lista numerada de carpetas y permite al usuario seleccionar una.
    folder_type: "base (juego base)" o "DLC"
    Retorna el nombre de la carpeta seleccionada, o None si cancela o no hay.
    """
    if not folders:
        print(f"\n  [AVISO] No se encontraron carpetas de {folder_type} (que empiecen con '{'0' if 'base' in folder_type else '1'} -').")
        return None

    print(f"\n--- Carpetas de {folder_type} disponibles ---")
    for i, name in enumerate(folders, 1):
        # Verificar si tiene subcarpeta strings/
        strings_path = os.path.join(BD_DIR, name, "strings")
        has_strings = os.path.exists(strings_path)
        status = "OK" if has_strings else "SIN strings/"
        print(f"  {i}. {name}  [{status}]")

    while True:
        try:
            choice = input(f"\n  Selecciona una carpeta [1-{len(folders)}] (0 = Ninguna): ").strip()
            idx = int(choice)
            if idx == 0:
                print(f"  No se usaran strings de {folder_type}.")
                return None
            if 1 <= idx <= len(folders):
                selected = folders[idx - 1]
                # Verificar que tenga subcarpeta strings/
                strings_path = os.path.join(BD_DIR, selected, "strings")
                if not os.path.exists(strings_path):
                    print(f"  [AVISO] La carpeta seleccionada no contiene subcarpeta 'strings/'.")
                    print(f"  Se intentara usar de todas formas.")
                return selected
            print(f"  Numero fuera de rango. Intenta de nuevo.")
        except ValueError:
            print("  Ingresa un numero valido.")
        except (KeyboardInterrupt, EOFError):
            print("\n  Operacion cancelada.")
            return None


def detect_language_from_folder(folder_name):
    """
    Intenta detectar el idioma basandose en el nombre de la carpeta.
    Retorna (lang_code, lang_info) o (None, None) si no se detecta.
    """
    folder_lower = folder_name.lower()

    for lang_code, lang_info in LANG_REFERENCE.items():
        for keyword in lang_info["folder_keywords"]:
            if keyword in folder_lower:
                return lang_code, lang_info

    return None, None


def get_input(prompt, default=""):
    """Pide input al usuario con un valor por defecto."""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


# ============================================================
# PARSER BINARIO
# ============================================================

def parse_strings_file(filepath):
    """
    Parsea un archivo .strings, .dlstrings o .ilstrings de Bethesda.
    Devuelve un diccionario: {stringID: texto}
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
    directory_size = num_entries * 8
    data_block_start = 8 + directory_size

    # Verificar tamaño
    expected_size = data_block_start + data_size
    if len(data) < expected_size:
        print(f"  [AVISO] Tamaño incorrecto en {os.path.basename(filepath)}: "
              f"esperado {expected_size}, tiene {len(data)}")

    # 2. Leer directorio y extraer strings
    for i in range(num_entries):
        dir_offset = 8 + (i * 8)

        if dir_offset + 8 > len(data):
            break

        string_id, string_offset = struct.unpack_from('<II', data, dir_offset)

        # El string_offset es RELATIVO al data block
        abs_offset = data_block_start + string_offset

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
            try:
                text = string_bytes.decode('latin-1')
            except:
                text = ""

        # Limpiar texto
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
            continue
        else:
            cleaned += ch

    # Remover espacios multiples
    cleaned = ' '.join(cleaned.split())

    return cleaned.strip()


# ============================================================
# EMPAREJAR Y CLASIFICAR
# ============================================================

def classify_entry(english, translation, source):
    """Clasifica una entrada por categoria y tipo"""
    en_lower = english.lower()

    category = "general"
    entry_type = ""

    # Lugares
    location_words = ["hold", "city", "town", "village", "keep", "castle",
                      "fort", "cave", "mine", "camp", "sanctuary", "temple",
                      "hall", "manor", "farm", "mill", "inn", "barracks",
                      "dungeon", "ruins", "barrow", "shrine", "tower", "sewer"]
    if any(w in en_lower for w in location_words):
        category = "lugar"

    # NPCs
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

    # Dialogo
    dialogue_verbs = ["i need", "i want", "i'm looking", "can you",
                      "would you", "have you", "do you", "what is",
                      "where is", "how do", "tell me", "let me",
                      "i don't", "i won't", "you must", "you should"]
    if any(w in en_lower for w in dialogue_verbs):
        category = "dialogo"
        entry_type = "dialogo"

    word_count = len(english.split())
    if word_count <= 2 and category == "general":
        entry_type = "nombre"

    if word_count > 8 and category == "general":
        category = "descripcion"
        entry_type = "descripcion"

    return category, entry_type


def match_entries(en_entries, tr_entries, source_name, lang_field):
    """
    Empareja entradas inglesas con las del idioma destino por stringID.
    lang_field: nombre del campo para la traduccion (ej: "spanish", "russian")
    """
    pairs = []
    matched = 0
    no_match = 0

    for string_id, en_text in en_entries.items():
        if not en_text.strip():
            continue

        tr_text = tr_entries.get(string_id, "")

        if not tr_text.strip():
            no_match += 1
            continue

        category, entry_type = classify_entry(en_text, tr_text, source_name)

        pairs.append({
            "english": en_text.strip(),
            lang_field: tr_text.strip(),
            "category": category,
            "type": entry_type,
            "source": source_name,
        })
        matched += 1

    return pairs, matched, no_match


# ============================================================
# PROCESAR ARCHIVOS
# ============================================================

def process_strings_file_pair(en_dir, tr_dir, base_name, source_name, file_suffixes, lang_field):
    """
    Procesa un par de archivos .strings (ingles + idioma destino).
    file_suffixes: lista de sufijos a probar (ej: ["_spanish", "_espanol"])
    lang_field: nombre del campo de traduccion (ej: "spanish")
    """
    results = []

    suffixes = [".strings", ".dlstrings", ".ilstrings"]
    suffix_names = ["strings", "dlstrings", "ilstrings"]

    for suffix, suffix_name in zip(suffixes, suffix_names):
        # Nombres de archivo ingleses (siempre _english)
        en_paths = [
            os.path.join(en_dir, f"{base_name}_english{suffix}"),
            os.path.join(en_dir, f"{base_name}{suffix}"),
        ]

        # Nombres de archivo del idioma destino (probar todos los sufijos)
        tr_paths = []
        for lang_suffix in file_suffixes:
            tr_paths.append(os.path.join(tr_dir, f"{base_name}{lang_suffix}{suffix}"))
        # Ultimo intento: sin sufijo de idioma
        tr_paths.append(os.path.join(tr_dir, f"{base_name}{suffix}"))

        # Buscar archivos que existan
        en_file = None
        tr_file = None

        for p in en_paths:
            if os.path.exists(p):
                en_file = p
                break

        for p in tr_paths:
            if os.path.exists(p):
                tr_file = p
                break

        if not en_file or not tr_file:
            continue

        print(f"  Procesando: {os.path.basename(en_file)} + {os.path.basename(tr_file)}")

        en_entries = parse_strings_file(en_file)
        tr_entries = parse_strings_file(tr_file)

        print(f"    EN: {len(en_entries)} entradas | Destino: {len(tr_entries)} entradas")

        full_source = f"{source_name}_{suffix_name}"
        pairs, matched, no_match = match_entries(en_entries, tr_entries, full_source, lang_field)
        results.extend(pairs)

        print(f"    Pares encontrados: {matched} | Sin traduccion: {no_match}")

    return results


def scan_all_strings(en_dir, tr_dir, file_suffixes, lang_field):
    """
    Escanea todas las carpetas buscando archivos .strings
    para el idioma destino seleccionado.
    """
    all_entries = []

    if not os.path.exists(en_dir) or not os.path.exists(tr_dir):
        return all_entries

    for filename in sorted(os.listdir(en_dir)):
        if not filename.endswith('.strings'):
            continue

        # Construir el nombre base: remover _english y la extension
        base = filename.replace('.strings', '').replace('.dlstrings', '').replace('.ilstrings', '')
        base = base.replace('_english', '').replace('_English', '')

        # Buscar el archivo del idioma destino correspondiente
        tr_file = None
        for lang_suffix in file_suffixes:
            candidate = filename.replace('_english', lang_suffix).replace('_English', lang_suffix.capitalize())
            candidate_path = os.path.join(tr_dir, candidate)
            if os.path.exists(candidate_path):
                tr_file = candidate_path
                break

        if not tr_file:
            same_name_path = os.path.join(tr_dir, filename)
            if os.path.exists(same_name_path):
                tr_file = same_name_path

        en_file = os.path.join(en_dir, filename)

        if tr_file and os.path.exists(tr_file):
            print(f"  Encontrado par: {os.path.basename(en_file)} + {os.path.basename(tr_file)}")
            en_entries = parse_strings_file(en_file)
            tr_entries = parse_strings_file(tr_file)

            source = base.replace('_', ' ')
            pairs, matched, no_match = match_entries(en_entries, tr_entries, source, lang_field)
            all_entries.extend(pairs)
            print(f"    EN: {len(en_entries)} | Destino: {len(tr_entries)} | Pares: {matched}")

    return all_entries


# ============================================================
# FLUJO PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("CREADOR DE GLOSARIO SKYRIM - MULTILENGUAJE")
    print("=" * 60)

    # -------------------------------------------------------
    # 1. Verificar carpeta BD
    # -------------------------------------------------------
    if not os.path.exists(BD_DIR):
        print(f"\n[ERROR] No se encontro la carpeta BD/: {BD_DIR}")
        print("Crea la carpeta BD/ con los strings del juego.")
        sys.exit(1)

    # -------------------------------------------------------
    # 2. Verificar que existen las carpetas de ingles
    # -------------------------------------------------------
    en_base_exists = os.path.exists(EN_BASE)
    en_dlc_exists = os.path.exists(EN_DLC)

    if not en_base_exists and not en_dlc_exists:
        print(f"\n[ERROR] No se encontraron carpetas de strings en ingles:")
        print(f"  Base: {EN_BASE}")
        print(f"  DLC:  {EN_DLC}")
        print("\nLas carpetas de English son obligatorias (son el source fijo).")
        print("Deben llamarse:")
        print('  "0 - English Original Strings/strings/"')
        print('  "1 - English DLC Strings/strings/"')
        sys.exit(1)

    print(f"\nStrings ingles (source fijo):")
    print(f"  Base: {'OK' if en_base_exists else 'NO ENCONTRADO'} - {EN_BASE}")
    print(f"  DLC:  {'OK' if en_dlc_exists else 'NO ENCONTRADO'} - {EN_DLC}")

    # -------------------------------------------------------
    # 3. Escanear carpetas disponibles en BD/
    # -------------------------------------------------------
    base_folders, dlc_folders = scan_bd_folders()

    print(f"\nCarpetas detectadas en BD/:")
    print(f"  Juego base (0 - *): {len(base_folders)} carpeta(s)")
    print(f"  DLC (1 - *):        {len(dlc_folders)} carpeta(s)")

    if not base_folders and not dlc_folders:
        print("\n[ERROR] No se encontraron carpetas de idiomas destino.")
        print("Necesitas carpetas como:")
        print('  "0 - Spanish Original Strings/strings/"')
        print('  "0 - Russian Original Strings/strings/"')
        print('  "1 - Spanish DLC Strings/strings/"')
        print('  etc.')
        sys.exit(1)

    # -------------------------------------------------------
    # 4. Seleccionar carpeta de juego base
    # -------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("PASO 1: Seleccionar carpeta de strings del JUEGO BASE")
    print(f"{'=' * 60}")

    selected_base = select_folder_from_list(base_folders, "juego base")

    # -------------------------------------------------------
    # 5. Seleccionar carpeta de DLC
    # -------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("PASO 2: Seleccionar carpeta de strings de DLC")
    print(f"{'=' * 60}")

    selected_dlc = select_folder_from_list(dlc_folders, "DLC")

    if not selected_base and not selected_dlc:
        print("\n[ERROR] No se selecciono ninguna carpeta de strings. No hay nada que procesar.")
        sys.exit(1)

    # Mostrar resumen de seleccion
    print(f"\n{'=' * 60}")
    print("RESUMEN DE CARPETAS SELECCIONADAS:")
    print(f"{'=' * 60}")
    print(f"  English Base: {'OK' if en_base_exists else 'NO'} - {EN_BASE}")
    print(f"  English DLC:  {'OK' if en_dlc_exists else 'NO'} - {EN_DLC}")
    if selected_base:
        print(f"  Destino Base: {selected_base}")
    if selected_dlc:
        print(f"  Destino DLC:  {selected_dlc}")

    # -------------------------------------------------------
    # 6. Detectar idioma automaticamente (sugerencia)
    # -------------------------------------------------------
    # Intentar detectar a partir de la carpeta base, si no de la DLC
    detected_code = None
    detected_info = None

    detect_from = selected_base or selected_dlc
    if detect_from:
        detected_code, detected_info = detect_language_from_folder(detect_from)

    if detected_info:
        print(f"\n  Idioma detectado automaticamente: {detected_info['name']} ({detected_code})")
        suggested_field = detected_info['name'].lower().replace(" ", "_")
        suggested_code = detected_code
    else:
        print(f"\n  No se pudo detectar el idioma automaticamente.")
        suggested_field = ""
        suggested_code = ""

    # -------------------------------------------------------
    # 7. Pedir nombre del campo de traduccion para el JSON
    # -------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("PASO 3: Nombre del campo de traduccion en el JSON")
    print(f"{'=' * 60}")
    print("  Este sera el nombre del campo que contiene la traduccion.")
    print('  Ejemplo: si escribes "spanish", las entradas seran:')
    print('    {"english": "Whiterun", "spanish": "Blancorruna", ...}')
    print('  Si escribes "russian":')
    print('    {"english": "Whiterun", "russian": "Вайтран", ...}')

    lang_field = get_input("\n  Nombre del campo de traduccion", suggested_field)
    if not lang_field:
        print("  [ERROR] Debes indicar un nombre para el campo de traduccion.")
        sys.exit(1)

    # Normalizar: minusculas, espacios por underscore
    lang_field = lang_field.lower().replace(" ", "_")

    # -------------------------------------------------------
    # 8. Pedir codigo para el nombre del archivo
    # -------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("PASO 4: Codigo para el nombre del archivo")
    print(f"{'=' * 60}")
    print("  Este codigo se usara en el nombre del archivo JSON.")
    print("  Ejemplo: si escribes 'es', el archivo sera:")
    print("    skyrim_glossary_en_es.json")
    print("  Si escribes 'ru':")
    print("    skyrim_glossary_en_ru.json")

    lang_code = get_input("\n  Codigo para el archivo", suggested_code)
    if not lang_code:
        print("  [ERROR] Debes indicar un codigo para el nombre del archivo.")
        sys.exit(1)

    # Normalizar: minusculas, sin espacios
    lang_code = lang_code.lower().replace(" ", "_")

    # -------------------------------------------------------
    # 9. Confirmar configuracion
    # -------------------------------------------------------
    OUTPUT_FILE = os.path.join(BD_DIR, f"skyrim_glossary_en_{lang_code}.json")

    print(f"\n{'=' * 60}")
    print("CONFIGURACION FINAL:")
    print(f"{'=' * 60}")
    print(f"  Carpeta Base destino:    {selected_base or '(ninguna)'}")
    print(f"  Carpeta DLC destino:     {selected_dlc or '(ninguna)'}")
    print(f"  Campo de traduccion:     \"{lang_field}\"")
    print(f"  Codigo de idioma:        {lang_code}")
    print(f"  Archivo de salida:       {os.path.basename(OUTPUT_FILE)}")
    print(f"  Ejemplo de entrada JSON:")
    print(f'    {{"english": "Whiterun", "{lang_field}": "...", "category": "lugar", ...}}')

    confirm = input(f"\n  Confirmar? [S/n]: ").strip().lower()
    if confirm in ('n', 'no'):
        print("  Operacion cancelada.")
        sys.exit(0)

    # -------------------------------------------------------
    # 10. Determinar sufijos de archivo .strings
    # -------------------------------------------------------
    # Si detectamos el idioma, usamos sus sufijos conocidos
    # Si no, generamos sufijos genericos a partir del campo y la carpeta
    if detected_info:
        file_suffixes = detected_info["file_suffixes"]
    else:
        # Generar sufijos probables
        file_suffixes = [
            f"_{lang_field}",
            f"_{lang_field.capitalize()}",
            f"_{lang_code}",
        ]
        # Si tenemos nombre de carpeta, extraer el idioma y agregar como sufijo
        if selected_base:
            # Extraer parte del idioma: "0 - Spanish Original Strings" -> "spanish"
            parts = selected_base.split(" - ", 1)
            if len(parts) > 1:
                lang_part = parts[1].split()[0].lower()
                file_suffixes.append(f"_{lang_part}")
                file_suffixes.append(f"_{lang_part.capitalize()}")

    # Agregar sufijos adicionales para PT-BR
    if "brazil" in lang_field or "pt_br" == lang_code or "ptbr" == lang_code:
        file_suffixes.extend(["_brazilian", "_Brazilian", "_portuguese", "_Portuguese"])

    # Eliminar duplicados manteniendo orden
    seen_suffixes = set()
    unique_suffixes = []
    for s in file_suffixes:
        if s not in seen_suffixes:
            seen_suffixes.add(s)
            unique_suffixes.append(s)
    file_suffixes = unique_suffixes

    print(f"\n  Sufijos de archivo a buscar: {file_suffixes}")

    # -------------------------------------------------------
    # 11. Procesar strings
    # -------------------------------------------------------
    all_entries = []

    # Procesar strings del juego base
    if en_base_exists and selected_base:
        TR_BASE = os.path.join(BD_DIR, selected_base, "strings")
        if os.path.exists(TR_BASE):
            print(f"\n--- Strings del juego base (EN -> {lang_field}) ---")
            for base_name, source_name in STRING_FILES:
                print(f"\nBuscando: {base_name}")
                pairs = process_strings_file_pair(EN_BASE, TR_BASE, base_name, source_name, file_suffixes, lang_field)
                all_entries.extend(pairs)
        else:
            print(f"\n[AVISO] No existe la subcarpeta strings/ en: {selected_base}")

    # Procesar strings de DLC
    if en_dlc_exists and selected_dlc:
        TR_DLC = os.path.join(BD_DIR, selected_dlc, "strings")
        if os.path.exists(TR_DLC):
            print(f"\n--- Strings de DLC (EN -> {lang_field}) ---")
            for base_name, source_name in STRING_FILES:
                print(f"\nBuscando: {base_name}")
                pairs = process_strings_file_pair(EN_DLC, TR_DLC, base_name, f"{source_name}_dlc", file_suffixes, lang_field)
                all_entries.extend(pairs)
        else:
            print(f"\n[AVISO] No existe la subcarpeta strings/ en: {selected_dlc}")

    # Si no hay entradas, buscar todos los .strings en las carpetas
    if not all_entries:
        print(f"\n[AVISO] No se encontraron entradas con los nombres esperados.")
        print("Buscando todos los archivos .strings disponibles...")

        if en_base_exists and selected_base:
            TR_BASE = os.path.join(BD_DIR, selected_base, "strings")
            all_entries.extend(scan_all_strings(EN_BASE, TR_BASE, file_suffixes, lang_field))

        if en_dlc_exists and selected_dlc:
            TR_DLC = os.path.join(BD_DIR, selected_dlc, "strings")
            all_entries.extend(scan_all_strings(EN_DLC, TR_DLC, file_suffixes, lang_field))

    if not all_entries:
        print(f"\n[ERROR] No se encontraron archivos .strings para procesar.")
        print("Asegurate de que los archivos esten en las carpetas correctas.")
        print(f"  Sufijos buscados: {file_suffixes}")
        sys.exit(1)

    # -------------------------------------------------------
    # 12. Deduplicar y limpiar
    # -------------------------------------------------------
    print(f"\nTotal antes de deduplicar: {len(all_entries)}")
    seen = {}
    unique_entries = []
    for entry in all_entries:
        key = entry["english"].lower().strip()
        if key not in seen:
            seen[key] = entry
            unique_entries.append(entry)
        else:
            existing = seen[key]
            if not existing.get(lang_field, "").strip() and entry.get(lang_field, "").strip():
                idx = unique_entries.index(existing)
                unique_entries[idx] = entry
                seen[key] = entry

    all_entries = unique_entries
    print(f"Total despues de deduplicar: {len(all_entries)}")

    # Eliminar entradas sospechosas
    clean_entries = []
    removed = 0
    for entry in all_entries:
        en = entry.get("english", "").strip()
        tr = entry.get(lang_field, "").strip()

        if len(en) <= 1:
            removed += 1
            continue

        if not tr:
            removed += 1
            continue

        clean_entries.append(entry)

    if removed > 0:
        print(f"Entradas removidas (vacias o corruptas): {removed}")
        print(f"Total limpio: {len(clean_entries)}")

    all_entries = clean_entries

    # -------------------------------------------------------
    # 13. Guardar JSON
    # -------------------------------------------------------
    print(f"\nGuardando glosario en: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Guardar como array directo (formato simple, compatible con el editor)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"Glosario guardado: {len(all_entries)} entradas")
    print(f"Archivo: {OUTPUT_FILE}")

    # Estadisticas
    print(f"\n--- Estadisticas por categoria ({lang_field}) ---")
    categories = {}
    for entry in all_entries:
        cat = entry.get("category", "sin_categoria")
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Verificar entradas importantes
    print(f"\n--- Verificacion de terminos clave (EN -> {lang_field}) ---")
    test_terms = ["whiterun", "stormcloaks", "windhelm", "solitude",
                  "imperial legion", "dragonborn", "thu'um", "daedra"]
    en_lookup = {e["english"].lower(): e for e in all_entries}

    for term in test_terms:
        if term in en_lookup:
            e = en_lookup[term]
            tr_val = e.get(lang_field, "???")
            print(f"  OK: {e['english']} -> {tr_val}")
        else:
            found = [e for e in all_entries if term in e["english"].lower()]
            if found:
                print(f"  PARCIAL: '{term}' encontrado en {len(found)} entradas")
                for e in found[:3]:
                    tr_val = e.get(lang_field, "???")
                    print(f"    {e['english']} -> {tr_val}")
            else:
                print(f"  NO ENCONTRADO: '{term}'")

    print(f"\nListo! Glosario EN->{lang_field} creado.")
    print(f"Archivo: {os.path.basename(OUTPUT_FILE)}")
    print(f"Ahora ejecuta: 1_cargar_glosario.py (para cargar en ChromaDB)")


if __name__ == "__main__":
    main()

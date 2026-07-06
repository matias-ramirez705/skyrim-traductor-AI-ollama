"""
=====================================================
PASO 3: Cargar el glosario JSON en ChromaDB
(SOPORTE MULTILENGUAJE)
=====================================================
Este script detecta automaticamente los archivos
skyrim_glossary_en_[lang].json en la carpeta BD/,
permite seleccionar cual cargar si hay varios,
y lo carga en una base de datos vectorial ChromaDB
para que el agente de traduccion pueda buscar terminos.

SOPORTE MULTILENGUAJE:
----------------------
- Detecta todos los archivos skyrim_glossary_en_*.json en BD/
- Si hay varios, permite al usuario seleccionar cual cargar
- Cada glosario se carga en su propia coleccion de ChromaDB
  (ej: skyrim_terminology_es, skyrim_terminology_ru)
- Determina el campo de traduccion a partir del metadata del JSON
  o del nombre del archivo si no hay metadata

USO: python 1_cargar_glosario.py
"""

import json
import os
import sys
import glob

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

# Ruta donde se guardara la base de datos ChromaDB
CHROMA_DIR = os.path.join(BD_DIR, "chroma_db")

# ============================================================
# DETECCION Y SELECCION DE GLOSARIOS
# ============================================================

def detect_glossary_files():
    """
    Detecta todos los archivos skyrim_glossary_en_*.json en la carpeta BD/.
    Retorna una lista de diccionarios con info de cada glosario encontrado.
    """
    pattern = os.path.join(BD_DIR, "skyrim_glossary_en_*.json")
    files = glob.glob(pattern)

    glossaries = []

    for filepath in sorted(files):
        filename = os.path.basename(filepath)

        # Extraer codigo de idioma del nombre: skyrim_glossary_en_[lang].json
        prefix = "skyrim_glossary_en_"
        suffix = ".json"
        if filename.startswith(prefix) and filename.endswith(suffix):
            lang_code = filename[len(prefix):-len(suffix)]
        else:
            continue

        # Leer metadata del JSON si existe
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Formato nuevo: {"metadata": {...}, "entries": [...]}
            if isinstance(data, dict) and "metadata" in data and "entries" in data:
                metadata = data["metadata"]
                entries = data["entries"]
                entry_count = len(entries)
                target_lang_name = metadata.get("target_lang_name", lang_code)
                translation_field = metadata.get("translation_field", target_lang_name)
            # Formato antiguo: lista directa [{"english":..., "spanish":...}, ...]
            elif isinstance(data, list):
                entries = data
                entry_count = len(data)
                target_lang_name = lang_code
                translation_field = _detect_translation_field(data, lang_code)
            else:
                continue

        except (json.JSONDecodeError, IOError) as e:
            print(f"  [AVISO] Error leyendo {filename}: {e}")
            continue

        # Nombre de la coleccion en ChromaDB
        collection_name = f"skyrim_terminology_{lang_code}"

        # Verificar si la coleccion ya existe en ChromaDB
        chroma_exists = _check_chroma_collection_exists(collection_name)

        glossaries.append({
            "filepath": filepath,
            "filename": filename,
            "lang_code": lang_code,
            "lang_name": target_lang_name,
            "entry_count": entry_count,
            "translation_field": translation_field,
            "collection_name": collection_name,
            "chroma_exists": chroma_exists,
        })

    return glossaries


def _detect_translation_field(data, lang_code):
    """
    Detecta el campo de traduccion en un glosario de formato antiguo (lista).
    Busca entre los campos del primer entry para encontrar el que no sea
    'english', 'category', 'type', o 'source'.
    """
    if not data or not isinstance(data, list):
        return lang_code

    first_entry = data[0]
    known_fields = {"english", "category", "type", "source"}

    for key in first_entry.keys():
        if key not in known_fields:
            return key

    return lang_code


def _check_chroma_collection_exists(collection_name):
    """Verifica si una coleccion ya existe en ChromaDB."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collections = client.list_collections()
        return any(c.name == collection_name for c in collections)
    except:
        return False


def select_glossary(glossaries):
    """
    Muestra los glosarios disponibles y permite al usuario seleccionar uno o todos.
    Retorna el diccionario del glosario seleccionado, 'all', o None si cancela.
    """
    if not glossaries:
        return None

    if len(glossaries) == 1:
        g = glossaries[0]
        print(f"\nSolo se encontro un glosario: {g['filename']}")
        print(f"  Idioma: {g['lang_name']} | Campo: \"{g['translation_field']}\" | Entradas: {g['entry_count']}")
        return g

    print("\n" + "=" * 70)
    print("GLOSARIOS DISPONIBLES EN BD/:")
    print("=" * 70)
    for i, g in enumerate(glossaries, 1):
        chroma_status = "Cargado" if g["chroma_exists"] else "No cargado"
        print(f"  {i}. {g['filename']}")
        print(f"     Idioma: {g['lang_name']} | Campo: \"{g['translation_field']}\" | Entradas: {g['entry_count']} | ChromaDB: {chroma_status}")

    print(f"\n  Opciones: numero [1-{len(glossaries)}], 'a' = cargar todos, '0' = cancelar")

    while True:
        try:
            choice = input(f"\n  Selecciona: ").strip().lower()
            if choice == '0':
                print("  Operacion cancelada.")
                return None
            if choice == 'a':
                return 'all'
            idx = int(choice) - 1
            if 0 <= idx < len(glossaries):
                return glossaries[idx]
            print(f"  Numero fuera de rango. Intenta de nuevo.")
        except ValueError:
            print("  Ingresa un numero valido, 'a' para todos, o '0' para cancelar.")
        except (KeyboardInterrupt, EOFError):
            print("\n  Operacion cancelada.")
            return None


# ============================================================
# FUNCIONES DE CARGA
# ============================================================

def load_glossary(filepath):
    """
    Carga el glosario desde el archivo JSON.
    Soporta formato nuevo (metadata + entries) y antiguo (lista plana).
    Retorna: (entries, metadata)
    """
    print(f"Cargando glosario desde: {filepath}")

    if not os.path.exists(filepath):
        print(f"[ERROR] No se encontro el archivo: {filepath}")
        print("Asegurate de haber ejecutado primero 0_crear_glosario.py")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Formato nuevo: {"metadata": {...}, "entries": [...]}
    if isinstance(data, dict) and "metadata" in data and "entries" in data:
        metadata = data["metadata"]
        entries = data["entries"]
        print(f"Glosario cargado: {len(entries)} entradas")
        print(f"  Source: {metadata.get('source_lang_name', 'English')} -> "
              f"{metadata.get('target_lang_name', '???')}")
        print(f"  Campo de traduccion: \"{metadata.get('translation_field', '???')}\"")
        return entries, metadata

    # Formato antiguo: lista directa
    if isinstance(data, list):
        print(f"Glosario cargado (formato antiguo): {len(data)} entradas")
        lang_field = _detect_translation_field(data, "es")
        metadata = {
            "target_lang": "es",
            "target_lang_name": lang_field,
            "translation_field": lang_field,
        }
        return data, metadata

    print(f"[ERROR] Formato de archivo no reconocido: {filepath}")
    sys.exit(1)


def build_chromadb(glossary, chroma_dir, collection_name, lang_field, lang_code):
    """Construye la base de datos vectorial ChromaDB"""

    # Importar aqui para dar mensaje claro si no esta instalado
    try:
        import chromadb
    except ImportError:
        print("[ERROR] ChromaDB no esta instalado.")
        print("Ejecuta: pip install chromadb")
        sys.exit(1)

    print(f"\nConstruyendo base de datos vectorial...")
    print(f"  Directorio: {chroma_dir}")
    print(f"  Coleccion: {collection_name}")
    print(f"  Campo de traduccion: \"{lang_field}\"")

    # Crear cliente ChromaDB persistente
    client = chromadb.PersistentClient(path=chroma_dir)

    # Eliminar coleccion existente si existe (para actualizar)
    try:
        client.delete_collection(collection_name)
        print("  Coleccion anterior eliminada")
    except:
        pass

    # Crear nueva coleccion con metadata del idioma
    collection = client.create_collection(
        name=collection_name,
        metadata={
            "description": f"Terminologia oficial de Skyrim EN->{lang_field}",
            "source_lang": "en",
            "target_lang": lang_code,
            "translation_field": lang_field,
        }
    )

    # Preparar datos para ChromaDB
    ids = []
    documents = []
    metadatas = []

    for i, entry in enumerate(glossary):
        entry_id = f"term_{i}"

        # Documento: combinamos ingles y traduccion para busqueda bilingue
        translation = entry.get(lang_field, "")
        doc = f"{entry['english']} | {translation}"

        # Metadatos
        meta = {
            "english": entry["english"],
            lang_field: translation,
            "source": entry.get("source", ""),
            "type": entry.get("type", ""),
            "category": entry.get("category", ""),
        }

        ids.append(entry_id)
        documents.append(doc)
        metadatas.append(meta)

    # Insertar en lotes de 5000
    batch_size = 5000
    total_batches = (len(ids) + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        start = batch_num * batch_size
        end = min(start + batch_size, len(ids))

        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end]
        )
        print(f"  Lote {batch_num + 1}/{total_batches}: {end - start} entradas insertadas")

    print(f"\nBase de datos creada exitosamente!")
    print(f"  Total entradas: {collection.count()}")
    print(f"  Coleccion: {collection_name}")

    return collection


def test_search(collection, query, lang_field, n_results=5):
    """Prueba la busqueda en la base de datos"""
    print(f"\n--- Prueba de busqueda: '{query}' ---")

    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        translation = meta.get(lang_field, "???")
        print(f"  {i+1}. EN: {meta['english']} | {lang_field}: {translation} (dist: {distance:.3f})")


def process_glossary(glossary_info):
    """Procesa un glosario completo: cargar JSON, construir ChromaDB, probar"""
    filepath = glossary_info["filepath"]
    lang_code = glossary_info["lang_code"]
    lang_name = glossary_info["lang_name"]
    lang_field = glossary_info["translation_field"]
    collection_name = glossary_info["collection_name"]

    print(f"\n{'=' * 60}")
    print(f"PROCESANDO: English -> {lang_name} ({lang_code})")
    print(f"  Campo de traduccion: \"{lang_field}\"")
    print(f"{'=' * 60}")

    # 1. Cargar glosario
    glossary, metadata = load_glossary(filepath)

    # 2. Construir base de datos
    collection = build_chromadb(glossary, CHROMA_DIR, collection_name, lang_field, lang_code)

    # 3. Pruebas de busqueda
    print(f"\n{'=' * 60}")
    print(f"PRUEBAS DE BUSQUEDA (EN -> {lang_field})")
    print(f"{'=' * 60}")

    test_search(collection, "Whiterun", lang_field)
    test_search(collection, "Stormcloaks", lang_field)
    test_search(collection, "dragon shout Thu'um", lang_field)

    # 4. Estadisticas por categoria
    print(f"\n{'=' * 60}")
    print(f"ESTADISTICAS ({lang_field})")
    print(f"{'=' * 60}")

    categories = {}
    for entry in glossary:
        cat = entry.get("category", "sin_categoria")
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    return collection


def main():
    print("=" * 60)
    print("CARGADOR DE GLOSARIO A CHROMADB - MULTILENGUAJE")
    print("=" * 60)

    # Verificar que existe la carpeta BD
    if not os.path.exists(BD_DIR):
        print(f"\n[ERROR] No se encontro la carpeta BD/: {BD_DIR}")
        print("Asegurate de que la estructura de carpetas sea correcta.")
        sys.exit(1)

    # Detectar glosarios disponibles
    glossaries = detect_glossary_files()

    if not glossaries:
        print(f"\n[ERROR] No se encontraron archivos skyrim_glossary_en_*.json en BD/")
        print(f"Ruta buscada: {BD_DIR}")
        print("\nEjecuta primero 0_crear_glosario.py para crear un glosario.")
        sys.exit(1)

    print(f"\nSe encontraron {len(glossaries)} glosario(s):")
    for g in glossaries:
        status = "Cargado" if g["chroma_exists"] else "No cargado"
        print(f"  - {g['filename']} (campo: \"{g['translation_field']}\", {g['entry_count']} entradas, {status})")

    # Seleccionar glosario
    selected = select_glossary(glossaries)
    if not selected:
        sys.exit(0)

    # Procesar glosario(s) seleccionado(s)
    if selected == 'all':
        for g in glossaries:
            process_glossary(g)
    else:
        process_glossary(selected)

    print(f"\n{'=' * 60}")
    print(f"PROCESO COMPLETADO")
    print(f"{'=' * 60}")
    print(f"Base de datos guardada en: {CHROMA_DIR}")
    print(f"\nAhora puedes ejecutar el servidor de traduccion (2_servidor_traduccion.py)")


if __name__ == "__main__":
    main()

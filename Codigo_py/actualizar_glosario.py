"""
=====================================================
ACTUALIZADOR DE GLOSARIO - Agrega terminos nuevos
=====================================================
Agrega terminos de un JSON nuevo a la base de datos
ChromaDB existente SIN tener que recargar todo.

Compatible con:
  - Python 3.11.9
  - chromadb >= 1.0

USO: python actualizar_glosario.py

Como funciona:
1. Lee el archivo JSON con terminos nuevos
2. Busca cuales ya existen en ChromaDB (para no duplicar)
3. Agrega solo los terminos nuevos

Formato del JSON de palabras agregadas:
[
  {
    "english": "Whiterun",
    "spanish": "Carrera Blanca",
    "category": "lugar",
    "source": "manual"
  },
  ...
]
"""

import json
import os
import sys

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
CHROMA_DIR = os.path.join(BASE_DIR, "BD", "chroma_db")
COLLECTION_NAME = "skyrim_terminology"
NUEVO_JSON = os.path.join(BASE_DIR, "BD", "palabras_agregadas.json")

# ============================================================
# FUNCIONES
# ============================================================

def get_collection():
    """Obtiene la coleccion existente de ChromaDB"""
    try:
        import chromadb
    except ImportError:
        print("[ERROR] ChromaDB no instalado. Ejecuta: pip install chromadb")
        sys.exit(1)

    if not os.path.exists(CHROMA_DIR):
        print(f"[ERROR] No se encontro la base de datos en: {CHROMA_DIR}")
        print("Ejecuta primero: 3_iniciar_glosario.bat")
        sys.exit(1)

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"Base de datos encontrada: {collection.count()} terminos actuales")
        return collection
    except Exception:
        print(f"[ERROR] Coleccion '{COLLECTION_NAME}' no encontrada.")
        print("Ejecuta primero: 3_iniciar_glosario.bat")
        sys.exit(1)


def get_existing_english_terms(collection):
    """Obtiene todos los terminos en ingles que ya estan en la BD"""
    existing = set()

    try:
        all_data = collection.get(include=["metadatas"])
        for meta in all_data['metadatas']:
            en = meta.get('english', '').lower()
            if en:
                existing.add(en)
    except Exception as e:
        print(f"[AVISO] No se pudieron leer terminos existentes: {e}")

    return existing


def load_new_terms(filepath):
    """Carga los terminos nuevos desde un archivo JSON"""
    if not os.path.exists(filepath):
        print(f"[ERROR] No se encontro: {filepath}")
        print()
        print("Crea un archivo JSON llamado 'palabras_agregadas.json'")
        print("en la carpeta BD con este formato:")
        print()
        print('[{')
        print('  "english": "Custom Mod Name",')
        print('  "spanish": "Nombre del Mod Personalizado",')
        print('  "category": "lugar",')
        print('  "source": "manual"')
        print('}]')
        print()
        print("Tambien puedes colocar varios archivos JSON en la carpeta BD")
        print("y el script los leera todos automaticamente.")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        terms = json.load(f)

    return terms


def load_all_jsons_from_dir(directory):
    """Busca todos los archivos JSON en la carpeta BD (excepto el glosario principal)"""
    all_terms = []
    main_glossary = "skyrim_glossary_en_es.json"

    if not os.path.exists(directory):
        return all_terms

    for filename in os.listdir(directory):
        if not filename.endswith('.json'):
            continue
        if filename == main_glossary:
            continue

        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                terms = json.load(f)

            if isinstance(terms, list) and len(terms) > 0:
                print(f"  Encontrado: {filename} ({len(terms)} terminos)")
                all_terms.extend(terms)
            elif isinstance(terms, dict):
                for key, value in terms.items():
                    if isinstance(value, list):
                        print(f"  Encontrado: {filename} -> {key} ({len(value)} terminos)")
                        all_terms.extend(value)
        except Exception as e:
            print(f"  [AVISO] No se pudo leer {filename}: {e}")

    return all_terms


def add_terms_to_collection(collection, new_terms, existing_terms):
    """Agrega solo los terminos nuevos a la coleccion"""

    ids = []
    documents = []
    metadatas = []
    skipped = 0

    current_count = collection.count()

    for i, term in enumerate(new_terms):
        en_text = term.get("english", "").strip()
        es_text = term.get("spanish", "").strip()

        if not en_text or not es_text:
            skipped += 1
            continue

        if en_text.lower() in existing_terms:
            skipped += 1
            continue

        entry_id = f"term_{current_count + len(ids)}"
        doc = f"{en_text} | {es_text}"

        meta = {
            "english": en_text,
            "spanish": es_text,
            "source": term.get("source", "manual"),
            "type": term.get("type", ""),
            "category": term.get("category", "general"),
        }

        ids.append(entry_id)
        documents.append(doc)
        metadatas.append(meta)
        existing_terms.add(en_text.lower())

    if not ids:
        print("\nNo hay terminos nuevos para agregar (todos ya existian).")
        return 0

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
        print(f"  Lote {batch_num + 1}/{total_batches}: {end - start} terminos agregados")

    if skipped > 0:
        print(f"  Saltados: {skipped} (ya existian o sin traduccion)")

    return len(ids)


def main():
    print("=" * 60)
    print("ACTUALIZADOR DE GLOSARIO")
    print("=" * 60)
    print()

    collection = get_collection()
    initial_count = collection.count()

    print("Buscando terminos existentes...")
    existing_terms = get_existing_english_terms(collection)
    print(f"Terminos existentes en BD: {len(existing_terms)}")

    print("\nBuscando archivos con terminos nuevos...")

    all_new_terms = []
    bd_dir = os.path.join(BASE_DIR, "BD")

    if os.path.exists(NUEVO_JSON):
        terms = load_new_terms(NUEVO_JSON)
        print(f"  palabras_agregadas.json: {len(terms)} terminos")
        all_new_terms.extend(terms)

    other_terms = load_all_jsons_from_dir(bd_dir)
    if other_terms:
        all_new_terms.extend(other_terms)

    if not all_new_terms:
        print("\nNo se encontraron terminos nuevos para agregar.")
        print()
        print("Para agregar terminos, crea un archivo llamado")
        print("'palabras_agregadas.json' en la carpeta BD con este formato:")
        print()
        print('[{')
        print('  "english": "Custom Place",')
        print('  "spanish": "Lugar Personalizado",')
        print('  "category": "lugar",')
        print('  "source": "manual"')
        print('}]')
        return

    print(f"\nTotal terminos nuevos encontrados: {len(all_new_terms)}")

    print("\nAgregando terminos nuevos a la base de datos...")
    added = add_terms_to_collection(collection, all_new_terms, existing_terms)

    final_count = collection.count()

    print("\n" + "=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"Terminos antes:  {initial_count}")
    print(f"Terminos nuevos: {added}")
    print(f"Terminos ahora:  {final_count}")
    print()
    print("Base de datos actualizada correctamente!")
    print("No necesitas reiniciar el servidor si esta corriendo.")
    print("Los terminos nuevos estaran disponibles inmediatamente.")


if __name__ == "__main__":
    main()

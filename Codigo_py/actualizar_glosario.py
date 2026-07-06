"""
=====================================================
ACTUALIZADOR DE GLOSARIO - Agrega terminos nuevos
(SOPORTE MULTILENGUAJE)
=====================================================
Agrega terminos de un JSON nuevo a la base de datos
ChromaDB existente SIN tener que recargar todo.

Detecta las colecciones disponibles en ChromaDB y
permite seleccionar cual actualizar.

USO: python actualizar_glosario.py

Como funciona:
1. Detecta colecciones ChromaDB disponibles (skyrim_terminology_es, _ru, etc.)
2. Permite seleccionar cual actualizar
3. Lee el archivo JSON con terminos nuevos
4. Busca cuales ya existen (para no duplicar)
5. Agrega solo los terminos nuevos

Formato del JSON de palabras agregadas:
[
  {
    "english": "Whiterun",
    "spanish": "Carrera Blanca",   <- o "russian", "portuguese", etc.
    "category": "lugar",
    "source": "manual"
  },
  ...
]
"""

import json
import os
import sys
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
CHROMA_DIR = os.path.join(BD_DIR, "chroma_db")


def _detect_translation_field(entries):
    """Detecta el campo de traduccion en las entradas."""
    if not entries:
        return "spanish"
    known = {"english", "category", "type", "source"}
    for key in entries[0].keys():
        if key not in known:
            return key
    return "spanish"


def detect_collections():
    """Detecta colecciones ChromaDB disponibles."""
    try:
        import chromadb
    except ImportError:
        print("[ERROR] ChromaDB no instalado. Ejecuta: pip install chromadb")
        sys.exit(1)

    if not os.path.exists(CHROMA_DIR):
        return []

    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collections = client.list_collections()
        result = []
        for c in collections:
            if c.name.startswith("skyrim_terminology"):
                lang_code = c.name.replace("skyrim_terminology_", "")
                if lang_code.startswith("_"):
                    lang_code = lang_code[1:]
                # Intentar obtener el campo de traduccion desde metadata
                tr_field = lang_code
                try:
                    meta = c.metadata or {}
                    tr_field = meta.get("translation_field", lang_code)
                except:
                    pass
                result.append({
                    "name": c.name,
                    "lang_code": lang_code,
                    "translation_field": tr_field,
                    "count": c.count(),
                })
        return result
    except Exception as e:
        print(f"[AVISO] Error leyendo ChromaDB: {e}")
        return []


def select_collection(collections):
    """Muestra colecciones y permite seleccionar una."""
    if not collections:
        return None
    if len(collections) == 1:
        c = collections[0]
        print(f"\nSolo se encontro una coleccion: {c['name']} ({c['count']} terminos)")
        return c

    print(f"\n{'=' * 60}")
    print("COLECCIONES CHROMADB DISPONIBLES:")
    print(f"{'=' * 60}")
    for i, c in enumerate(collections, 1):
        print(f"  {i}. {c['name']} ({c['count']} terminos, campo: \"{c['translation_field']}\")")

    while True:
        try:
            choice = input(f"\nSelecciona [1-{len(collections)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(collections):
                return collections[idx]
            print("Numero fuera de rango.")
        except ValueError:
            print("Ingresa un numero valido.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperacion cancelada.")
            return None


def get_collection(collection_name):
    """Obtiene la coleccion existente de ChromaDB."""
    import chromadb

    if not os.path.exists(CHROMA_DIR):
        print(f"[ERROR] No se encontro la base de datos en: {CHROMA_DIR}")
        print("Ejecuta primero: 3_iniciar_glosario.bat")
        sys.exit(1)

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        collection = client.get_collection(collection_name)
        return collection
    except Exception:
        print(f"[ERROR] Coleccion '{collection_name}' no encontrada.")
        print("Ejecuta primero: 3_iniciar_glosario.bat")
        sys.exit(1)


def get_existing_english_terms(collection):
    """Obtiene todos los terminos en ingles que ya estan en la BD."""
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


def load_all_jsons_from_dir(directory, lang_field):
    """Busca todos los archivos JSON en la carpeta BD (excepto glosarios principales)."""
    all_terms = []
    # Excluir los glosarios principales (skyrim_glossary_en_*.json)
    main_pattern = "skyrim_glossary_en_"

    if not os.path.exists(directory):
        return all_terms

    for filename in os.listdir(directory):
        if not filename.endswith('.json'):
            continue
        if filename.startswith(main_pattern):
            continue

        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                terms = json.load(f)

            if isinstance(terms, list) and len(terms) > 0:
                # Detectar campo de traduccion
                detected_field = _detect_translation_field(terms)
                print(f"  Encontrado: {filename} ({len(terms)} terminos, campo: \"{detected_field}\")")
                all_terms.extend(terms)
            elif isinstance(terms, dict):
                for key, value in terms.items():
                    if isinstance(value, list):
                        print(f"  Encontrado: {filename} -> {key} ({len(value)} terminos)")
                        all_terms.extend(value)
        except Exception as e:
            print(f"  [AVISO] No se pudo leer {filename}: {e}")

    return all_terms


def add_terms_to_collection(collection, new_terms, existing_terms, lang_field):
    """Agrega solo los terminos nuevos a la coleccion."""
    ids = []
    documents = []
    metadatas = []
    skipped = 0

    current_count = collection.count()

    for i, term in enumerate(new_terms):
        en_text = term.get("english", "").strip()
        tr_text = term.get(lang_field, "").strip()

        if not en_text or not tr_text:
            skipped += 1
            continue

        if en_text.lower() in existing_terms:
            skipped += 1
            continue

        entry_id = f"term_{current_count + len(ids)}"
        doc = f"{en_text} | {tr_text}"

        meta = {
            "english": en_text,
            lang_field: tr_text,
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
    print("ACTUALIZADOR DE GLOSARIO - MULTILENGUAJE")
    print("=" * 60)
    print()

    # Detectar colecciones disponibles
    collections = detect_collections()
    if not collections:
        print(f"[ERROR] No se encontraron colecciones ChromaDB en: {CHROMA_DIR}")
        print("Ejecuta primero: 3_iniciar_glosario.bat")
        sys.exit(1)

    # Seleccionar coleccion
    selected = select_collection(collections)
    if not selected:
        sys.exit(0)

    collection_name = selected["name"]
    lang_field = selected["translation_field"]

    print(f"\nActualizando coleccion: {collection_name}")
    print(f"  Campo de traduccion: \"{lang_field}\"")

    collection = get_collection(collection_name)
    initial_count = collection.count()
    print(f"Terminos actuales: {initial_count}")

    # Buscar terminos existentes
    print("Buscando terminos existentes...")
    existing_terms = get_existing_english_terms(collection)
    print(f"Terminos unicos en BD: {len(existing_terms)}")

    # Buscar archivos con terminos nuevos
    print("\nBuscando archivos con terminos nuevos...")

    all_new_terms = []

    # Buscar palabras_agregadas_[lang].json o palabras_agregadas.json
    palabras_files = [
        os.path.join(BD_DIR, f"palabras_agregadas_{selected['lang_code']}.json"),
        os.path.join(BD_DIR, "palabras_agregadas.json"),
    ]
    for pf in palabras_files:
        if os.path.exists(pf):
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    terms = json.load(f)
                if isinstance(terms, list):
                    print(f"  {os.path.basename(pf)}: {len(terms)} terminos")
                    all_new_terms.extend(terms)
            except Exception as e:
                print(f"  [AVISO] Error leyendo {os.path.basename(pf)}: {e}")
            break  # Usar solo el primero que encuentre

    # Buscar otros JSON en la carpeta
    other_terms = load_all_jsons_from_dir(BD_DIR, lang_field)
    if other_terms:
        all_new_terms.extend(other_terms)

    if not all_new_terms:
        print("\nNo se encontraron terminos nuevos para agregar.")
        print()
        print(f"Para agregar terminos, crea un archivo llamado")
        print(f"'palabras_agregadas_{selected['lang_code']}.json' en la carpeta BD con este formato:")
        print()
        print('[{')
        print('  "english": "Custom Place",')
        print(f'  "{lang_field}": "Lugar Personalizado",')
        print('  "category": "lugar",')
        print('  "source": "manual"')
        print('}]')
        return

    print(f"\nTotal terminos nuevos encontrados: {len(all_new_terms)}")

    # Detectar campo de traduccion en los terminos nuevos
    if all_new_terms:
        detected_field = _detect_translation_field(all_new_terms)
        if detected_field != lang_field:
            print(f"\n[AVISO] Los terminos nuevos usan campo \"{detected_field}\" pero la coleccion usa \"{lang_field}\"")
            print(f"  Se usara el campo de la coleccion: \"{lang_field}\"")

    print("\nAgregando terminos nuevos a la base de datos...")
    added = add_terms_to_collection(collection, all_new_terms, existing_terms, lang_field)

    final_count = collection.count()

    print("\n" + "=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"Coleccion:      {collection_name}")
    print(f"Terminos antes: {initial_count}")
    print(f"Terminos nuevos: {added}")
    print(f"Terminos ahora: {final_count}")
    print()
    print("Base de datos actualizada correctamente!")
    print("No necesitas reiniciar el servidor si esta corriendo.")
    print("Los terminos nuevos estaran disponibles inmediatamente.")


if __name__ == "__main__":
    main()

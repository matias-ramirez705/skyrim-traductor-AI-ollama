"""
=====================================================
PASO 3: Cargar el glosario JSON en ChromaDB
=====================================================
Este script lee el archivo skyrim_glossary_en_es.json
y lo carga en una base de datos vectorial ChromaDB
para que el agente de traduccion pueda buscar terminos.

USO: python 1_cargar_glosario.py
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

# Ruta del glosario JSON
GLOSSARY_FILE = os.path.join(BASE_DIR, "BD", "skyrim_glossary_en_es.json")

# Ruta donde se guardara la base de datos ChromaDB
CHROMA_DIR = os.path.join(BASE_DIR, "BD", "chroma_db")

# Nombre de la coleccion en ChromaDB
COLLECTION_NAME = "skyrim_terminology"

# ============================================================
# FUNCIONES
# ============================================================

def load_glossary(filepath):
    """Carga el glosario desde el archivo JSON"""
    print(f"Cargando glosario desde: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"[ERROR] No se encontro el archivo: {filepath}")
        print("Asegurate de haber ejecutado primero crear_glosario.py")
        sys.exit(1)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        glossary = json.load(f)
    
    print(f"Glosario cargado: {len(glossary)} entradas")
    return glossary


def build_chromadb(glossary, chroma_dir, collection_name):
    """Construye la base de datos vectorial ChromaDB"""
    
    # Importar aqui para dar mensaje claro si no esta instalado
    try:
        import chromadb
    except ImportError:
        print("[ERROR] ChromaDB no esta instalado.")
        print("Ejecuta: pip install chromadb")
        sys.exit(1)
    
    print(f"\nConstruyendo base de datos vectorial en: {chroma_dir}")
    
    # Crear cliente ChromaDB persistente (se guarda en disco)
    client = chromadb.PersistentClient(path=chroma_dir)
    
    # Eliminar coleccion existente si existe (para actualizar)
    try:
        client.delete_collection(collection_name)
        print("  Coleccion anterior eliminada")
    except:
        pass
    
    # Crear nueva coleccion
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": "Terminologia oficial de Skyrim EN->ES"}
    )
    
    # Preparar datos para ChromaDB
    # ChromaDB necesita: ids, documents (texto para buscar), metadatos
    ids = []
    documents = []
    metadatas = []
    
    for i, entry in enumerate(glossary):
        # ID unico
        entry_id = f"term_{i}"
        
        # Documento: combinamos ingles y espanol para busqueda bilingue
        doc = f"{entry['english']} | {entry['spanish']}"
        
        # Metadatos: toda la info extra
        meta = {
            "english": entry["english"],
            "spanish": entry["spanish"],
            "source": entry.get("source", ""),
            "type": entry.get("type", ""),
            "category": entry.get("category", ""),
        }
        
        ids.append(entry_id)
        documents.append(doc)
        metadatas.append(meta)
    
    # Insertar en lotes de 5000 (ChromaDB tiene limite por lote)
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
    print(f"  Ubicacion: {chroma_dir}")
    
    return collection


def test_search(collection, query, n_results=5):
    """Prueba la busqueda en la base de datos"""
    print(f"\n--- Prueba de busqueda: '{query}' ---")
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        print(f"  {i+1}. EN: {meta['english']} | ES: {meta['spanish']} (dist: {distance:.3f})")


def main():
    print("=" * 60)
    print("CARGADOR DE GLOSARIO A CHROMADB")
    print("=" * 60)
    
    # 1. Cargar glosario
    glossary = load_glossary(GLOSSARY_FILE)
    
    # 2. Construir base de datos
    collection = build_chromadb(glossary, CHROMA_DIR, COLLECTION_NAME)
    
    # 3. Pruebas de busqueda
    print("\n" + "=" * 60)
    print("PRUEBAS DE BUSQUEDA")
    print("=" * 60)
    
    test_search(collection, "Whiterun")
    test_search(collection, "Stormcloaks")
    test_search(collection, "dragon shout Thu'um")
    test_search(collection, "magia hechizo conjuracion")
    test_search(collection, "espada daedrica armadura")
    
    # 4. Estadisticas por categoria
    print("\n" + "=" * 60)
    print("ESTADISTICAS")
    print("=" * 60)
    
    categories = {}
    for entry in glossary:
        cat = entry.get("category", "sin_categoria")
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    print(f"\nListo! La base de datos esta guardada en: {CHROMA_DIR}")
    print("Ahora puedes ejecutar el servidor de traduccion (2_servidor_traduccion.py)")


if __name__ == "__main__":
    main()

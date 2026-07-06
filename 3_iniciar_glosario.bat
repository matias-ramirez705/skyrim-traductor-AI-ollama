@echo off
echo ============================================================
echo   PASO 3: Cargar glosario en ChromaDB
echo   (Soporte multilenguaje - seleccion interactiva)
echo ============================================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual en venv\
    echo Ejecuta primero: 2_instalar_dependencias.bat
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo Cargando glosario en la base de datos...
echo Si hay varios glosarios, se te pedira seleccionar cual cargar.
echo.

python Codigo_py\1_cargar_glosario.py

if errorlevel 1 (
    echo.
    echo [ERROR] Hubo un error al cargar el glosario.
    echo Revisa los mensajes de error arriba.
    echo.
)

echo.
echo ============================================================
echo   Si no hubo errores, la base de datos esta lista!
echo.
echo   Ahora ejecuta: 4_iniciar_servidor.bat
echo ============================================================
echo.

pause

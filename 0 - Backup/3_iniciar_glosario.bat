@echo off
echo ============================================================
echo   PASO 3: Cargar glosario en ChromaDB
echo ============================================================
echo.

cd /d "%~dp0"

echo Activando entorno virtual...
call venv\Scripts\activate.bat

echo.
echo Cargando glosario en la base de datos...
echo.

python Codigo_py\1_cargar_glosario.py

echo.
echo ============================================================
echo   Si no hubo errores, la base de datos esta lista!
echo.
echo   Ahora ejecuta: 4_iniciar_servidor.bat
echo ============================================================
echo.

pause

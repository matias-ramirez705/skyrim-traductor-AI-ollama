@echo off
echo ============================================================
echo   PASO 1: Crear glosario desde archivos .strings
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

echo Creando glosario a partir de los archivos .strings...
echo Se te pedira seleccionar:
echo   1. Carpeta de strings del juego base
echo   2. Carpeta de strings de DLC
echo   3. Nombre del campo de traduccion (ej: spanish, russian)
echo   4. Codigo para el archivo (ej: es, ru)
echo.
echo Esto puede tardar varios minutos.
echo.

python Codigo_py\0_crear_glosario.py

if errorlevel 1 (
    echo.
    echo [ERROR] Hubo un error al crear el glosario.
    echo Revisa los mensajes de error arriba.
    echo.
)

echo.
pause

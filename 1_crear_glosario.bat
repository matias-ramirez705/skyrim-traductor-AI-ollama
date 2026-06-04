@echo off
echo ============================================================
echo   PASO 1: Crear glosario desde archivos .strings
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
echo Esto puede tardar varios minutos.
echo.

python Codigo_py\crear_glosario.py

if errorlevel 1 (
    echo.
    echo [ERROR] Hubo un error al crear el glosario.
    echo Revisa los mensajes de error arriba.
    echo.
)

echo.
pause

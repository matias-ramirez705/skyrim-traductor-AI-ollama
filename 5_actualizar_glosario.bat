@echo off
echo ============================================================
echo   Actualizar glosario (agregar palabras nuevas)
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
echo Buscando palabras nuevas para agregar...
echo.

python Codigo_py\actualizar_glosario.py

if errorlevel 1 (
    echo.
    echo [ERROR] Hubo un error al actualizar.
    echo Revisa los mensajes de error arriba.
    echo.
)

echo.
pause

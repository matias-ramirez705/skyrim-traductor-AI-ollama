@echo off
echo ============================================================
echo   LIMPIAR glosario (eliminar entradas corruptas)
echo ============================================================
echo.
echo Esto eliminara entradas con texto vacio o corrupto del JSON.
echo Se creara un backup automaticamente.
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python Codigo_py\limpiar_glosario.py

echo.
pause

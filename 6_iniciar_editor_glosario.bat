@echo off
echo ====================================================
echo EDITOR DE GLOSARIO SKYRIM
echo ====================================================
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

echo Iniciando editor de glosario...
echo Se abrira en tu navegador: http://localhost:7861
echo.
echo Para detener, cierra esta ventana o presiona Ctrl+C
echo.

python Codigo_py\5_editor_glosario.py

if errorlevel 1 (
    echo.
    echo [ERROR] El editor se cerro con un error.
    echo Revisa los mensajes de error arriba.
    echo.
)

pause

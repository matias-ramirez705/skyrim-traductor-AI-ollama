@echo off
echo ============================================================
echo   PASO 2: Activar entorno virtual e instalar dependencias
echo ============================================================
echo.

cd /d "%~dp0"

echo Activando entorno virtual...
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo [ERROR] No se encontro el entorno virtual.
    echo Creandolo ahora...
    echo.
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        echo Asegurate de tener Python 3.11 instalado.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo.
echo Actualizando pip...
echo.
python -m pip install --upgrade pip

echo.
echo Desinstalando versiones viejas (si existen)...
echo.
pip uninstall -y gradio ollama chromadb 2>nul

echo.
echo Instalando dependencias con versiones compatibles...
echo Esto puede tardar unos minutos.
echo.

pip install "ollama>=0.4.0" "gradio>=5.0" "chromadb>=1.0.0"

echo.
echo Verificando instalacion...
echo.

python -c "import chromadb; print('  chromadb: ' + chromadb.__version__)" 2>nul
if errorlevel 1 (
    echo  [ERROR] chromadb no se instalo correctamente
) else (
    echo  [OK] chromadb
)

python -c "import ollama; print('  ollama: instalado correctamente')" 2>nul
if errorlevel 1 (
    echo  [ERROR] ollama no se instalo correctamente
) else (
    echo  [OK] ollama
)

python -c "import gradio; print('  gradio: ' + gradio.__version__)" 2>nul
if errorlevel 1 (
    echo  [ERROR] gradio no se instalo correctamente
) else (
    echo  [OK] gradio
)

echo.
echo ============================================================
echo   Instalacion completada!
echo.
echo   Ahora ejecuta: 3_iniciar_glosario.bat
echo ============================================================
echo.

pause
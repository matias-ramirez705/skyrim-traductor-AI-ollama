@echo off
echo ============================================================
echo   PASO 5: Iniciar servidor de traduccion
echo ============================================================
echo.

cd /d "%~dp0"

echo Activando entorno virtual...
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual en venv\
    echo Ejecuta primero: 2_instalar_dependencias.bat
    echo.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

echo.
echo Verificando que Ollama este ejecutandose...
echo.

ollama list >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Ollama no esta ejecutandose.
    echo.
    echo Intentando iniciar Ollama...
    start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"

    echo Esperando 10 segundos a que Ollama inicie...
    timeout /t 10 /nobreak >nul

    ollama list >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudo iniciar Ollama automaticamente.
        echo Por favor, abre Ollama manualmente desde el Menu de Inicio
        echo y vuelve a ejecutar este script.
        echo.
        pause
        exit /b 1
    )
)

echo Ollama esta funcionando!
echo.

echo Verificando modelo qwen2.5:7b...
ollama list | findstr "qwen2.5" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Modelo qwen2.5:7b no encontrado.
    echo Descargando modelo esto puede tardar 10-20 minutos...
    echo.
    ollama pull qwen2.5:7b
)

echo Modelo listo!
echo.
echo Iniciando servidor de traduccion...
echo Se abrira una ventana en tu navegador.
echo.
echo Para detener: cierra esta ventana o presiona Ctrl+C
echo ============================================================
echo.

python Codigo_py\2_servidor_traduccion.py

if errorlevel 1 (
    echo.
    echo [ERROR] El servidor se cerro con un error.
    echo Revisa los mensajes de error arriba.
    echo.
)

pause

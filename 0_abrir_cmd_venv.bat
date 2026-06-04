@echo off
title CMD con entorno virtual activado

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo.
    echo [ERROR] No se encontro:
    echo venv\Scripts\activate.bat
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo =====================================
echo Entorno virtual activado correctamente
echo =====================================
echo.

cmd /k
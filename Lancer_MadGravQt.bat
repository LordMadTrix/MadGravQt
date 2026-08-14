@echo off
setlocal enabledelayedexpansion
title MadGrav Qt6

:: Se positionner dans le dossier du script
cd /d "%~dp0"

:: 1. Verifier si l'environnement virtuel local .venv existe
if exist ".venv\Scripts\python.exe" (
    echo [MadGravQt] Demarrage de l'interface PyQt6...
    ".venv\Scripts\python.exe" run_qt.py
    if !errorlevel! neq 0 (
        echo.
        echo [ERREUR] Une erreur est survenue lors de l'execution.
        pause
    )
    exit /b !errorlevel!
)

:: 2. Recherche de Python global dans le PATH
where python.exe >nul 2>&1
if !errorlevel! equ 0 (
    echo [MadGravQt] Utilisation du Python systeme...
    python run_qt.py
    if !errorlevel! neq 0 (
        echo.
        echo [ERREUR] Une erreur est survenue lors de l'execution.
        pause
    )
    exit /b !errorlevel!
)

echo [ERREUR] Python introuvable !
echo Veuillez installer Python ou recreer l'environnement virtuel .venv.
pause

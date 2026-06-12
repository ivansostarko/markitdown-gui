@echo off
rem Build the Windows app + installer.
rem Requires: Python 3.10+, and optionally Inno Setup 6 (iscc on PATH) for the installer.

setlocal
cd /d "%~dp0.."

echo === Installing build dependencies ===
python -m pip install --upgrade pip || exit /b 1
python -m pip install ".[dev]" || exit /b 1

echo === Generating icons ===
python scripts\generate_icon.py || exit /b 1

echo === Building portable app with PyInstaller ===
python -m PyInstaller markitdown_gui.spec --noconfirm || exit /b 1

where iscc >nul 2>nul
if errorlevel 1 (
    echo.
    echo Inno Setup ^(iscc^) not found on PATH - skipping installer.
    echo Portable app is ready in dist\MarkItDownGUI\
    exit /b 0
)

echo === Compiling Windows installer with Inno Setup ===
iscc installers\windows\installer.iss || exit /b 1

echo.
echo Done!
echo   Portable app : dist\MarkItDownGUI\
echo   Installer    : installers\windows\Output\MarkItDownGUI-Setup.exe
endlocal

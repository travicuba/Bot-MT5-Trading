@echo off
REM build_installer.bat
REM Compila la app WPF y crea el instalador
REM Requiere: .NET SDK 8+, Inno Setup 6

echo =========================================
echo  Trading Bot Desktop - Build Installer
echo =========================================

REM Verificar .NET SDK
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: .NET SDK no encontrado.
    echo Instalar desde: https://dotnet.microsoft.com/download/dotnet/8.0
    pause
    exit /b 1
)

echo [1/3] Limpiando build anterior...
rd /s /q "TradingBotDesktop\bin\Release" 2>nul

echo [2/3] Compilando y publicando...
dotnet publish TradingBotDesktop\TradingBotDesktop.csproj ^
    -c Release ^
    -r win-x64 ^
    --self-contained true ^
    -p:PublishSingleFile=false ^
    -p:PublishReadyToRun=true

if errorlevel 1 (
    echo ERROR: Fallo la compilacion
    pause
    exit /b 1
)

echo [3/3] Creando instalador con Inno Setup...

REM Buscar Inno Setup en rutas comunes
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if %ISCC%=="" (
    echo.
    echo ADVERTENCIA: Inno Setup no encontrado.
    echo Para crear el instalador, instala Inno Setup 6 desde:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo Los archivos compilados estan en:
    echo TradingBotDesktop\bin\Release\net8.0-windows\win-x64\publish\
    pause
    exit /b 0
)

mkdir installer\output 2>nul
%ISCC% installer\setup.iss

if errorlevel 1 (
    echo ERROR: Fallo Inno Setup
    pause
    exit /b 1
)

echo.
echo =========================================
echo  BUILD COMPLETADO
echo  Instalador: installer\output\
echo =========================================
pause

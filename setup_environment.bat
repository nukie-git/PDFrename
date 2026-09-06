@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Force working directory to the directory of this batch script
cd /d "%~dp0."

echo ===================================================
echo   PDFrename Environment ^& Dependency Setup (v1.5.0)
echo   © nukie 2026
echo ===================================================
echo(

:check_runtime
REM 1. Check if Python is available
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%V in ('python --version 2^>^&1') do set "PY_VER=%%V"
    echo [FOUND] Python is installed: !PY_VER!
    set "RUNTIME_MODE=python"
    goto check_python_deps
)

REM 2. Check if uv is available
uv --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%V in ('uv --version 2^>^&1') do set "UV_VER=%%V"
    echo [FOUND] Astral uv is installed: !UV_VER!
    set "RUNTIME_MODE=uv"
    goto check_uv_ready
)

REM 3. Neither Python nor uv found in PATH. Check winget availability.
echo [WARNING] Neither Python nor uv is installed or detected in your PATH.
echo(

winget --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] winget package manager was not found on this system.
    echo Please install Python manually from: https://www.python.org/
    echo or install Astral uv manually from:  https://docs.astral.sh/uv/
    echo(
    pause
    exit /b 1
)

echo Windows Package Manager (winget) is available.
echo You can install a compatible runtime automatically:
echo(
echo   [1] Install Astral uv ^(Recommended - fast, lightweight, auto-manages dependencies^)
echo   [2] Install Python 3.12
echo   [3] Cancel and exit
echo(

set /p install_choice="Enter your choice (1, 2, or 3): "

if "!install_choice!"=="1" (
    echo(
    echo Installing Astral uv via winget...
    winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install uv via winget.
        pause
        exit /b 1
    )
    call :refresh_path
    uv --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARNING] uv was installed but is not yet in this session's PATH.
        echo Please restart your terminal or log off and back in.
        pause
        exit /b 1
    )
    echo [SUCCESS] uv installed and detected successfully!
    echo(
    set "RUNTIME_MODE=uv"
    goto check_uv_ready
)

if "!install_choice!"=="2" (
    echo(
    echo Installing Python 3.12 via winget...
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Python via winget.
        pause
        exit /b 1
    )
    call :refresh_path
    python --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARNING] Python was installed but is not yet in this session's PATH.
        echo Please restart your terminal or log off and back in.
        pause
        exit /b 1
    )
    echo [SUCCESS] Python installed and detected successfully!
    echo(
    set "RUNTIME_MODE=python"
    goto check_python_deps
)

echo Setup cancelled by user.
exit /b 1

:check_python_deps
echo(
echo Checking required Python dependencies (pypdf, pillow, rapidocr-onnxruntime)...
python -c "import pypdf, PIL, rapidocr_onnxruntime" >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] All required dependencies are installed.
    goto setup_complete
)

echo [INFO] Required dependencies are missing: pypdf, pillow, rapidocr-onnxruntime.
set /p dep_choice="Would you like to install missing dependencies now? (Y/N): "
if /i "!dep_choice!"=="Y" (
    echo Installing pypdf, pillow, and rapidocr-onnxruntime via pip...
    pip install pypdf pillow rapidocr-onnxruntime
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies via pip.
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed successfully.
    goto setup_complete
) else (
    echo [WARNING] Missing required dependencies.
    exit /b 1
)

:check_uv_ready
echo(
echo [INFO] Astral uv runtime is active.
echo Dependencies (pypdf, pillow, rapidocr-onnxruntime) are managed automatically
echo via PEP 723 inline script metadata upon workflow execution.
goto setup_complete

:setup_complete
echo(
echo Creating Desktop shortcuts...
cscript //nologo "%~dp0create-shortcut.vbs" silent >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] Desktop shortcuts created:
    echo   - Rename Downloads Receipts ^(PDFrename^)
    echo   - PDFrename Workflow ^(Custom or Drag-Drop Folder^)
) else (
    echo [WARNING] Could not create Desktop shortcuts automatically.
)

echo(
echo ===================================================
echo   Environment setup completed successfully!
echo ===================================================
echo(
exit /b 0

:refresh_path
REM Refresh PATH environment variable from User and System Registry
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do call set "USER_REG_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do call set "SYS_REG_PATH=%%B"
if defined USER_REG_PATH set "PATH=!USER_REG_PATH!;!PATH!"
if defined SYS_REG_PATH set "PATH=!SYS_REG_PATH!;!PATH!"

REM Append common installation locations if they exist
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;!PATH!"
if exist "%LOCALAPPDATA%\Programs\Python\Python312" set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
if exist "%LOCALAPPDATA%\Programs\Python\Python313" set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;!PATH!"
if exist "%LOCALAPPDATA%\bin" set "PATH=%LOCALAPPDATA%\bin;!PATH!"
if exist "%USERPROFILE%\.local\bin" set "PATH=%USERPROFILE%\.local\bin;!PATH!"
if exist "%USERPROFILE%\.cargo\bin" set "PATH=%USERPROFILE%\.cargo\bin;!PATH!"
exit /b 0

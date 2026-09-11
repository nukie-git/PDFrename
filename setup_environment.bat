@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Force working directory to the directory of this batch script
cd /d "%~dp0."

echo ===================================================
echo   PDFrename Environment ^& Dependency Setup (v1.7.0)
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
if !errorlevel! equ 0 (
    goto winget_available
)

:winget_missing
echo [INFO] Windows Package Manager (winget) was not detected on this system.
echo Choose how you would like to set up a compatible runtime:
echo(
echo   [1] Install Astral uv directly ^(Recommended - fast, zero dependencies, works on any Windows build^)
echo   [2] Bootstrap WinGet package manager via PowerShell, then install uv/Python
echo   [3] Download and install Python 3.12 directly ^(Official python.org installer^)
echo   [4] Cancel and exit
echo(

set /p no_winget_choice="Enter your choice (1, 2, 3, or 4): "

if "!no_winget_choice!"=="1" goto install_uv_direct
if "!no_winget_choice!"=="2" goto bootstrap_winget
if "!no_winget_choice!"=="3" goto install_python_direct

echo Setup cancelled by user.
exit /b 1

:winget_available
echo Windows Package Manager (winget) is available.
echo You can install a compatible runtime automatically:
echo(
echo   [1] Install Astral uv ^(Recommended - fast, lightweight, auto-manages dependencies^)
echo   [2] Install Python 3.12
echo   [3] Cancel and exit
echo(

set /p install_choice="Enter your choice (1, 2, or 3): "

if "!install_choice!"=="1" goto install_uv_winget
if "!install_choice!"=="2" goto install_python_winget

echo Setup cancelled by user.
exit /b 1

:install_uv_direct
echo(
echo Installing Astral uv directly via official installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://astral.sh/uv/install.ps1 | iex"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install uv directly via PowerShell.
    pause
    exit /b 1
)
call :refresh_path
uv --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] uv was installed but is not yet in this session's PATH.
    echo Checking user local binary paths...
    if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;!PATH!"
    if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "PATH=%USERPROFILE%\.cargo\bin;!PATH!"
    uv --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo Please restart your terminal or log off and back in.
        pause
        exit /b 1
    )
)
for /f "tokens=*" %%V in ('uv --version 2^>^&1') do set "UV_VER=%%V"
echo [SUCCESS] Astral uv installed and detected successfully: !UV_VER!
echo(
set "RUNTIME_MODE=uv"
goto check_uv_ready

:bootstrap_winget
echo(
echo Bootstrapping Windows Package Manager (winget)...
echo Downloading and installing WinGet and prerequisites via PowerShell...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference = 'SilentlyContinue'; " ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
    "try { " ^
    "    Write-Host 'Fetching WinGet installer package...'; " ^
    "    irm https://raw.githubusercontent.com/asheroto/winget-install/master/winget-install.ps1 | iex; " ^
    "} catch { " ^
    "    Write-Warning ('Automated script encountered an error: ' + $_.Exception.Message); " ^
    "    Write-Host 'Attempting direct AppX package download and registration...'; " ^
    "    $tmp = Join-Path $env:TEMP ('winget_' + [Guid]::NewGuid().ToString('N')); " ^
    "    New-Item -ItemType Directory -Force -Path $tmp | Out-Null; " ^
    "    $vclibs = Join-Path $tmp 'VCLibs.appx'; " ^
    "    $uiXaml = Join-Path $tmp 'UIXaml.appx'; " ^
    "    $bundle = Join-Path $tmp 'WinGet.msixbundle'; " ^
    "    Invoke-WebRequest -Uri 'https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx' -OutFile $vclibs -UseBasicParsing; " ^
    "    Invoke-WebRequest -Uri 'https://github.com/microsoft/microsoft-ui-xaml/releases/download/v2.8.6/Microsoft.UI.Xaml.2.8.x64.appx' -OutFile $uiXaml -UseBasicParsing; " ^
    "    Invoke-WebRequest -Uri 'https://github.com/microsoft/winget-cli/releases/latest/download/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle' -OutFile $bundle -UseBasicParsing; " ^
    "    Add-AppxPackage -Path $vclibs -ErrorAction SilentlyContinue; " ^
    "    Add-AppxPackage -Path $uiXaml -ErrorAction SilentlyContinue; " ^
    "    Add-AppxPackage -Path $bundle -DependencyPath $vclibs, $uiXaml; " ^
    "    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue; " ^
    "}"
if !errorlevel! neq 0 (
    echo [ERROR] WinGet bootstrapping failed.
    echo You may install Astral uv directly instead (Option 1), or install Python from https://www.python.org/
    pause
    exit /b 1
)
call :refresh_path
winget --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] WinGet was installed, but command execution alias is not yet active in this session.
    echo Checking WindowsApps path...
    if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe" set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;!PATH!"
    winget --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo WinGet requires a new terminal session or sign out/in to register the App Execution Alias.
        echo If you want to continue immediately without signing out, run setup again and choose Option 1 (Astral uv).
        pause
        exit /b 1
    )
)
echo [SUCCESS] WinGet is now available!
echo(
goto winget_available

:install_python_direct
echo(
echo Downloading Python 3.12 official installer from python.org...
set "PY_INSTALLER=%TEMP%\python-3.12.8-amd64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
    "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%PY_INSTALLER%' -UseBasicParsing"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to download Python 3.12 installer.
    pause
    exit /b 1
)
echo Running Python 3.12 installer...
"%PY_INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1
if !errorlevel! neq 0 (
    echo [ERROR] Python installation process exited with an error code.
    pause
    exit /b 1
)
del /f /q "%PY_INSTALLER%" >nul 2>&1
call :refresh_path
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] Python was installed but is not yet in this session's PATH.
    echo Please restart your terminal or log off and back in.
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('python --version 2^>^&1') do set "PY_VER=%%V"
echo [SUCCESS] Python installed and detected successfully: !PY_VER!
echo(
set "RUNTIME_MODE=python"
goto check_python_deps

:install_uv_winget
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

:install_python_winget
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

:check_python_deps
echo(
echo Checking required Python dependencies (pypdf, pillow, fonttools, rapidocr-onnxruntime, pdfplumber, pymupdf)...
python -c "import pypdf, PIL, fontTools, rapidocr_onnxruntime, pdfplumber, pymupdf" >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] All required dependencies are installed.
    goto setup_complete
)

echo [INFO] Required dependencies are missing: pypdf, pillow, fonttools, rapidocr-onnxruntime, pdfplumber, pymupdf.
set /p dep_choice="Would you like to install missing dependencies now? (Y/N): "
if /i "!dep_choice!"=="Y" (
    echo Installing dependencies via pip...
    REM Install lightweight packages together
    echo [1/4] Installing lightweight dependencies: pypdf, pillow, fonttools
    pip install pypdf pillow fonttools
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install lightweight dependencies via pip.
        pause
        exit /b 1
    )
    REM Install larger packages singularly to avoid parallel download saturation
    echo [2/4] Installing pdfplumber
    pip install pdfplumber
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install pdfplumber via pip.
        pause
        exit /b 1
    )
    echo [3/4] Installing rapidocr-onnxruntime
    pip install rapidocr-onnxruntime
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install rapidocr-onnxruntime via pip.
        pause
        exit /b 1
    )
    echo [4/4] Installing pymupdf
    pip install pymupdf
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install pymupdf via pip.
        pause
        exit /b 1
    )
    echo [SUCCESS] All dependencies installed successfully.
    goto setup_complete
) else (
    echo [WARNING] Missing required dependencies.
    exit /b 1
)

:check_uv_ready
echo(
echo [INFO] Astral uv runtime is active.
echo Dependencies (pypdf, pillow, rapidocr-onnxruntime, fonttools, pdfplumber, pymupdf) are managed automatically
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
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps" set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;!PATH!"
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;!PATH!"
if exist "%LOCALAPPDATA%\Programs\Python\Python312" set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
if exist "%LOCALAPPDATA%\Programs\Python\Python313" set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;!PATH!"
if exist "%LOCALAPPDATA%\bin" set "PATH=%LOCALAPPDATA%\bin;!PATH!"
if exist "%USERPROFILE%\.local\bin" set "PATH=%USERPROFILE%\.local\bin;!PATH!"
if exist "%USERPROFILE%\.cargo\bin" set "PATH=%USERPROFILE%\.cargo\bin;!PATH!"
exit /b 0

@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Force working directory to the directory of this batch script
cd /d "%~dp0."

REM Set target directory to Downloads
set "TARGET_DIR=%USERPROFILE%\Downloads"

echo ===================================================
echo   PDF Transaction Receipt Renaming Workflow Tool
echo   © nukie 2026
echo   Target Folder: !TARGET_DIR!
echo ===================================================
echo(

:detect_runtime
REM 1. Check if Python is available
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXEC=python"
    set "USING_UV=0"
    goto check_dependencies
)

REM 2. Check if uv is available
uv --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXEC=uv run"
    set "USING_UV=1"
    echo [INFO] Python command not found in PATH, using Astral uv.
    goto check_dependencies
)

REM 3. Neither runtime found, call setup_environment.bat
echo [WARNING] Neither Python nor uv is installed or detected in your PATH.
echo Launching environment setup...
echo(
call "%~dp0setup_environment.bat"
if !errorlevel! neq 0 (
    echo [ERROR] Environment setup was not completed. Cannot proceed.
    pause
    exit /b 1
)
goto detect_runtime

:check_dependencies
if !USING_UV! equ 0 (
    REM Check dependencies: pypdf, pillow, fonttools, rapidocr-onnxruntime, pdfplumber, pymupdf
    python -c "import pypdf, PIL, fontTools, rapidocr_onnxruntime, pdfplumber, pymupdf" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [INFO] Required Python dependencies are missing: pypdf, pillow, fonttools, rapidocr-onnxruntime, pdfplumber, pymupdf.
        set /p install_choice="Would you like to install missing dependencies now? (Y/N): "
        if /i "!install_choice!"=="Y" (
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
        ) else (
            echo [WARNING] Missing required dependencies. Cannot run rename workflow.
            pause
            exit /b 1
        )
    )
) else (
    echo [INFO] Using uv runtime - dependencies are managed automatically via PEP 723 metadata.
)

echo(
echo Running dry run preview on: !TARGET_DIR!
echo ---------------------------------------------------
!PYTHON_EXEC! dry_run_rename.py "!TARGET_DIR!"
set "DRY_RUN_EXIT=!errorlevel!"

if !DRY_RUN_EXIT! equ 2 (
    echo ---------------------------------------------------
    goto end_process
)

if !DRY_RUN_EXIT! neq 0 if !DRY_RUN_EXIT! neq 3 (
    echo ---------------------------------------------------
    echo [ERROR] Dry run did not complete successfully ^(exit code !DRY_RUN_EXIT!^).
    echo No valid preview was generated - aborting instead of prompting to rename.
    goto end_process
)
echo ---------------------------------------------------
echo(

if !DRY_RUN_EXIT! equ 3 (
    echo [WARNING] Proposed filename conflicts were detected and disambiguated with numbered suffixes.
    set /p execute_choice="Filename conflicts exist. Would you still like to proceed with renaming? (Y/N): "
) else (
    set /p execute_choice="Would you like to proceed with the actual renaming? (Y/N): "
)

if /i "!execute_choice!"=="Y" (
    echo(
    echo Executing renaming...
    !PYTHON_EXEC! execute_rename.py "!TARGET_DIR!"
) else (
    echo Renaming aborted by user.
)

:end_process
REM Pending mapping snapshot cleanup is owned by execute_rename.py, not this script.

echo(
echo Process complete.
pause

@echo off
setlocal enabledelayedexpansion

REM Force working directory to the directory of this batch script
cd /d "%~dp0."

REM Set target directory to Downloads
set "TARGET_DIR=%USERPROFILE%\Downloads"

echo ===================================================
echo   PDF Transaction Receipt Renaming Workflow Tool
echo   Target Folder: !TARGET_DIR!
echo ===================================================
echo(

REM Check Python installation
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH environment variable.
    echo Please install Python from https://www.python.org/ and try again.
    pause
    exit /b 1
)

REM Check dependencies (pypdf, pillow, rapidocr-onnxruntime)
python -c "import pypdf, PIL, rapidocr_onnxruntime" >nul 2>&1
if !errorlevel! neq 0 (
    echo [INFO] Required Python dependencies are missing: pypdf, pillow, rapidocr-onnxruntime.
    set /p install_choice="Would you like to install missing dependencies now? (Y/N): "
    if /i "!install_choice!"=="Y" (
        echo Installing pypdf, pillow, and rapidocr-onnxruntime...
        pip install pypdf pillow rapidocr-onnxruntime
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to install dependencies. Please run 'pip install pypdf pillow rapidocr-onnxruntime' manually.
            pause
            exit /b 1
        )
        echo [SUCCESS] Dependencies installed successfully.
    ) else (
        echo [WARNING] Missing required dependencies. Cannot run rename workflow.
        pause
        exit /b 1
    )
)

echo(
echo Running dry run preview on: !TARGET_DIR!
echo ---------------------------------------------------
python dry_run_rename.py "!TARGET_DIR!"
set "DRY_RUN_EXIT=!errorlevel!"

if !DRY_RUN_EXIT! equ 2 (
    echo ---------------------------------------------------
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
    python execute_rename.py "!TARGET_DIR!"
) else (
    echo Renaming aborted by user.
)

:end_process
if exist "!TARGET_DIR!\.rename_cache.json" del /f /q "!TARGET_DIR!\.rename_cache.json" >nul 2>&1

echo(
echo Process complete.
pause

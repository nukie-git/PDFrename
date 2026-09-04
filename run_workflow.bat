@echo off
setlocal enabledelayedexpansion

REM Force working directory to the directory of this batch script
cd /d "%~dp0."

REM Target directory can be passed as argument %1 or defaults to current directory
if "%~1"=="" (
    set "TARGET_DIR=."
) else (
    set "TARGET_DIR=%~1"
)

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

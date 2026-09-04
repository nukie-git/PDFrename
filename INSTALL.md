# Installation & How-To Guide (v1.5.0)

This guide explains how to install and run the PDF Transaction Receipt & Bon Renaming workflow in a clean Windows environment or Google Antigravity workspace.

---

## 1. Directory Structure
Extract the contents of this ZIP file directly into the **root** of your target project folder.
Ensure the files are placed as follows:
```
[Your Project Root Folder]/
├── rename.md
├── INSTALL.md
├── README.md
├── .gitignore             <-- Git ignore file (includes .venv/, logs/, *.pdf)
├── setup_environment.bat  <-- Environment & dependency setup (Python / uv / winget)
├── create-shortcut.vbs    <-- VBScript desktop shortcut creator
├── run_workflow.bat       <-- General Runner (Accepts target folder parameter or drag-and-drop)
├── rename_workflow.bat    <-- Specific Runner (Defaults to %USERPROFILE%\Downloads)
├── dry_run_rename.py      <-- Dry run preview scanner & OCR parser (PEP 723 enabled)
├── execute_rename.py      <-- Rename executor (renames strictly from logs/pending_mapping.json)
├── logger.py              <-- Daily rotating logger (keeps last 7 log files)
├── logs/                  <-- Auto-created folder for daily logs (YYYYMMDD.log) and pending_mapping.json
└── .agents/
    └── rules/
        └── rename_workflow.md
```

---

## 2. Desktop Shortcut Setup
Desktop shortcuts are **automatically created** when running `setup_environment.bat` (or upon completing initial runtime setup).
You can also re-create them manually at any time by double-clicking **`create-shortcut.vbs`**:
- **`Rename Downloads Receipts (PDFrename)`**: 1-click execution for files in `%USERPROFILE%\Downloads`.
- **`PDFrename Workflow (Custom or Drag-Drop Folder)`**: Drag and drop any folder directly onto this shortcut to process and rename receipts inside that folder!

---

## 3. Running via Windows Command Line
- To rename files in the **current folder**, double-click `run_workflow.bat`.
- To rename files in the **Downloads folder** (`%USERPROFILE%\Downloads`), double-click `rename_workflow.bat`.
- Alternatively, drag and drop any target folder onto `run_workflow.bat`.

The batch file will automatically:
1. **Detect Runtime**:
   - Checks if `python` is available.
   - If Python is not found, automatically falls back to Astral **`uv`** (`uv run`).
   - If neither is found, seamlessly launches `setup_environment.bat` which prompts you to install either Astral `uv` or Python 3.12 via `winget`, refreshes your session `PATH`, and resumes workflow execution.
2. **Resolve Dependencies**:
   - If using `python`: checks for `pypdf`, `pillow`, and `rapidocr-onnxruntime` and prompts to install them via `pip install`.
   - If using `uv`: dependencies are automatically managed via PEP 723 inline script metadata (`# /// script`) in an isolated cache.
3. **Dry Run Preview**: Runs the preview scan on the target folder (performing OCR for scanned image PDFs if needed).
4. **Pending Snapshot**: Saves the exact previewed mapping to `logs/pending_mapping.json`.
5. **Visual Preview**: Displays the visual preview table of proposed changes — collision warnings with `(1)`, `(2)` suffixes if any, and `⚠️` warnings on any row that was a fallback guess rather than a confident read.
6. **Safety Abort**: If the dry run failed to complete, safely aborts without modifying files.
7. **User Confirmation**: Prompts whether you want to proceed with the actual renaming.
8. **Preview-Locked Execution**: Renames files strictly according to `logs/pending_mapping.json` (with Windows 2-step case-safe renaming and rollback on error), then cleans up the snapshot.
9. **Daily Rotating Logs**: Writes execution details into daily logs in `logs/YYYYMMDD.log` (7-day retention).

---

## 4. Running via Google Antigravity Workspace
1. Open the project folder as a workspace in **Google Antigravity**.
2. Start a new chat session and simply type:
   ```
   start
   ```
3. The agent will run the dry run preview (using `python` or `uv run`), present the visual comparison table directly in the chat (flagging any `⚠️` low-confidence rows), and prompt you (`yes`/`no`) before applying any renaming.

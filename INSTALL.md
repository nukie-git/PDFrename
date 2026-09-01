# Installation & How-To Guide (v1.3.3)

This guide explains how to install and run the PDF Transaction Receipt & Bon Renaming workflow in a clean Windows environment or Google Antigravity workspace.

---

## 1. Directory Structure
Extract the contents of this ZIP file directly into the **root** of your target project folder.
Ensure the files are placed as follows:
```
[Your Project Root Folder]/
├── rename.md
├── INSTALL.md
├── .gitignore             <-- Python and project ignore file
├── run_workflow.bat       <-- General Runner (Accepts target folder parameter)
├── rename_workflow.bat    <-- Specific Runner (Defaults to %USERPROFILE%\Downloads)
├── dry_run_rename.py      <-- Dry run preview scanner & OCR parser
├── execute_rename.py      <-- Rename executor (renames strictly from logs/pending_mapping.json)
├── logger.py               <-- Daily rotating logger (keeps last 7 log files)
├── logs/                  <-- Auto-created folder for daily logs (YYYYMMDD.log) and pending_mapping.json
└── .agents/
    └── rules/
        └── rename_workflow.md
```

---

## 2. Running via Windows Command Line (Easiest)
- To rename files in the **current folder**, double-click `run_workflow.bat`.
- To rename files in the **Downloads folder** (`%USERPROFILE%\Downloads`), double-click `rename_workflow.bat`.
- Alternatively, run `run_workflow.bat "%USERPROFILE%\Downloads"` from the Command Prompt (`cmd.exe`).
The batch file will automatically:
1. Check if Python is installed on your system.
2. Check if the required libraries (`pypdf`, `pillow`, `rapidocr-onnxruntime`) are installed. If missing, it will ask to install them for you automatically.
3. Directly run the **dry run preview** scan on the target folder (performing OCR for scanned image PDFs if needed).
4. Save the exact previewed mapping to `logs/pending_mapping.json`.
5. Show the visual preview table of proposed changes — collision warnings with `(1)`, `(2)` suffixes if any, and `⚠️` warnings on any row that was a fallback guess rather than a confident read (check these before approving).
6. If the dry run failed to complete (any exit code other than "no files found" or "conflicts found"), abort here instead of asking you to rename — nothing was safely previewed.
7. Ask you if you want to proceed with the **actual renaming**.
8. Rename files strictly from `logs/pending_mapping.json` — refusing instead of silently re-scanning if that snapshot is missing, for a different folder, or over an hour old — then delete the snapshot.
9. Write execution details into daily logs in `logs/YYYYMMDD.log` (keeping the last 7 log files).

---

## 3. Running via Google Antigravity Workspace
1. Open the project folder as a workspace in **Google Antigravity**.
2. Start a new chat session and simply type:
   ```
   start
   ```
3. The agent will run the dry run preview, present the visual comparison table directly in the chat (flagging any `⚠️` low-confidence rows), and prompt you (`yes`/`no`) before applying any renaming.



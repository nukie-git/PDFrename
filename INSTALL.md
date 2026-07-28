# Installation & How-To Guide

This guide explains how to install and run the PDF Transaction Receipt Renaming workflow in a clean Windows environment or Google Antigravity workspace.

---

## 1. Directory Structure
Extract the contents of this ZIP file directly into the **root** of your target project folder.
Ensure the files are placed as follows:
```
[Your Project Root Folder]/
├── rename.md
├── INSTALL.md
├── .gitignore             <-- Added (Python and project ignore file)
├── run_workflow.bat       <-- General Runner (Accepts target folder parameter)
├── rename_workflow.bat    <-- Specific Runner (Defaults to %USERPROFILE%\Downloads)
├── dry_run_rename.py
├── execute_rename.py
├── logger.py               <-- Daily rotating logger (keeps last 7 log files)
├── logs/                  <-- Auto-created daily log folder (YYYYMMDD.log)
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
2. Check if the required library `pypdf` is installed. If missing, it will ask to install it for you automatically.
3. Directly run the **dry run preview** scan on the target folder.
4. Show the visual preview table of proposed changes (including collision warnings with `(1)`, `(2)` suffixes if any).
5. Ask you if you want to proceed with the **actual renaming**.
6. Write execution details into daily logs in `logs/YYYYMMDD.log` (keeping the last 7 log files).

---

## 3. Running via Google Antigravity Workspace
1. Open the project folder as a workspace in **Google Antigravity**.
2. Start a new chat session and simply type:
   ```
   start
   ```
3. The agent will run the dry run preview, present the visual comparison table directly in the chat, and prompt you (`yes`/`no`) before applying any renaming.

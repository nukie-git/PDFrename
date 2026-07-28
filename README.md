# PDFrename

**PDFrename** is an automated transaction receipt renaming workflow tool for Bank Mandiri (KOPRA) transfer proofs. It parses PDF transaction receipts, extracts metadata (Creation Date, Beneficiary, Remark), normalizes formatting, resolves filename collisions, and safely renames files for effortless archiving.

---

## 🌟 Key Features

- **Automated Metadata Parsing**: Extracts `Creation Date`, `Destination Account` (beneficiary), and `Remark` directly from receipt PDF text using `pypdf`.
- **Standardized Naming Convention**: Renames files using the format:
  $$\text{\{YYYYMMDD\}} \quad \text{\{Receiver\}} \quad \text{\{Remark\}}.pdf$$
  *Example*: `20260728 Muhamad Fahmi Raihan Sul pembelian sayuran bale.pdf`
- **Title Case Normalization**: Converts raw receiver names (e.g. `DEDE MADIN` $\rightarrow$ `Dede Madin`).
- **Path Portability**: Supports `%USERPROFILE%\Downloads` and environment variable expansion across Windows environments.
- **Automatic Collision Resolution**: Detects duplicate proposed filenames or existing files on disk and automatically appends disambiguated suffixes like `(1)`, `(2)`, `(3)`.
- **Daily Rotating Logs (`logs/YYYYMMDD.log`)**: Automatically logs dry runs, file renames, errors, and warnings into `logs/` with a **7-day retention policy**.
- **Safe 2-Step Windows Renaming**: Uses temporary files (`.tmp_rename`) during renaming to support Windows case-only filename updates cleanly.

---

## 🚀 Quick Start

### 1. Rename Downloads Receipts (Easiest)
Double-click **`rename_workflow.bat`**.  
It defaults to `%USERPROFILE%\Downloads`, runs the preview table directly, and prompts for confirmation before executing the rename.

### 2. Rename a Custom Folder
Run `run_workflow.bat` from Command Prompt (`cmd.exe`):
```cmd
run_workflow.bat "C:\path\to\your\receipts"
```

---

## 📁 Project Structure

```
PDFrename/
├── dry_run_rename.py         # Parses PDFs, generates preview table, handles collision resolution
├── execute_rename.py         # Applies safe file renaming on disk
├── logger.py                 # Daily rotating logger module (keeps 7 most recent log files)
├── rename_workflow.bat       # Windows runner defaulting to %USERPROFILE%\Downloads
├── run_workflow.bat          # Generic Windows runner (accepts custom target path)
├── rename.md                 # Detailed SOP and naming specification document
├── INSTALL.md                # Installation and setup guide
├── .gitignore                # Git ignore configuration (ignores *.pdf, logs/, *.log, zip)
└── logs/                     # Auto-generated daily log directory (YYYYMMDD.log)
```

---

## 🪵 Logging System

All script operations (scans, counts, error logs, conflict resolution, renames) are logged automatically into `logs/YYYYMMDD.log`.
Old log files beyond the 7 most recent days are automatically pruned.

---

## 📜 License
[MIT License](LICENSE)

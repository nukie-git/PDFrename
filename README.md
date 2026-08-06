# PDFrename `v1.1.1`

**PDFrename** is an automated transaction receipt & bon scan renaming workflow tool for Bank Mandiri (KOPRA) transfer proofs and image-based bon receipts. It parses PDF receipts, extracts metadata and document dates via text/OCR, normalizes formatting, resolves filename collisions, and safely renames files for effortless archiving.

---

## 🌟 Key Features

- **Automated Metadata Parsing**: Extracts `Creation Date`, `Destination Account` (beneficiary), and `Remark` directly from Mandiri transfer receipt text using `pypdf`.
- **Image-Based Bon Scan OCR Support**: Automatically detects scanned PDFs (`IMG_YearMonthDate_*`), runs OCR on embedded images via `rapidocr-onnxruntime` to extract handwritten/printed receipt dates, and renames them to `bon_bentang_YearMonthDate.pdf`.
- **Instant Execution Caching (`.rename_cache.json`)**: Caches pre-computed rename mappings during dry run preview to make the actual file renaming execution instant (< 10ms).
- **Strict Cache File Cleanup**: Automatically purges temporary `.rename_cache.json` files via Python `finally` blocks and batch script traps upon completion or cancellation.
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
├── dry_run_rename.py         # Parses PDFs/OCR, generates preview table, caches mapping
├── execute_rename.py         # Instant file renamer using pre-computed cache
├── logger.py                 # Daily rotating logger module (keeps 7 most recent log files)
├── rename_workflow.bat       # Windows runner defaulting to %USERPROFILE%\Downloads
├── run_workflow.bat          # Generic Windows runner (accepts custom target path)
├── rename.md                 # Detailed SOP and naming specification document
├── INSTALL.md                # Installation and setup guide
├── .gitignore                # Git ignore configuration (ignores *.pdf, logs/, cache)
└── logs/                     # Auto-generated daily log directory (YYYYMMDD.log)
```

---

## 🪵 Logging System

All script operations (scans, counts, error logs, conflict resolution, renames) are logged automatically into `logs/YYYYMMDD.log`.
Old log files beyond the 7 most recent days are automatically pruned.

---

## 📋 Changelog

### `v1.1.1` (2026-08-06)
- **Automatic Cache File Cleanup**: Guaranteed purging of `.rename_cache.json` after execution, cancellation, or abort via Python `finally` handlers and batch exit traps.
- **Batch Script Syntax Fix**: Resolved Windows `cmd.exe` crash (`. was unexpected at this time`) by fixing unescaped parenthesis syntax in `if` blocks and enforcing CRLF line endings.

### `v1.1.0` (2026-08-06)
- **Scanned Bon OCR Feature**: Added support for image-based PDFs (`IMG_YearMonthDate_*`). Uses `rapidocr-onnxruntime` to extract handwritten/printed receipt dates inside the document.
- **Instant Execution Cache**: Added `.rename_cache.json` caching mechanism between dry run scan and file rename execution to eliminate redundant OCR processing.
- **Dependency Automation**: Added auto-installation checks for `pillow` and `rapidocr-onnxruntime` in batch scripts.

### `v1.0.0` (2026-08-06)
- Initial release with Bank Mandiri KOPRA transfer receipt parsing, Title Case normalization, collision resolution, and daily rotating logs.

---

## 📜 License
[MIT License](LICENSE)

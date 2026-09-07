# PDFrename `v1.6.0`

**PDFrename** is an automated transaction receipt & bon scan renaming workflow tool for Bank Mandiri (KOPRA) transfer proofs and image-based bon receipts. It parses PDF receipts, extracts metadata and document dates via text/OCR, normalizes formatting, resolves filename collisions, and safely renames files for effortless archiving.

---

## 🌟 Key Features

- **Automated Metadata Parsing & Multi-Engine Text Extraction**: Extracts `Creation Date`, `Destination Account` (beneficiary), and `Remark` directly from Mandiri transfer receipts. Implements an adaptive multi-tier text extraction pipeline (`pypdf` + `fonttools` + `pymupdf` + `pdfplumber`) to handle embedded fonts lacking `/ToUnicode` maps and Word/Excel converted receipts.
- **GitHub Repository Auto-Updater (`updater.py`)**: Checks the remote GitHub repository (`https://github.com/nukie-git/PDFrename`) on script start. If updates are found, it downloads and stages the update, prompting you to either restart immediately with the update or continue processing first and finalize the update automatically upon completion.
- **Multi-Layer Bon Scan OCR**: Runs `rapidocr-onnxruntime` on scanned bon PDFs (`IMG_YearMonthDate_*`). A single OCR pass feeds both a **date** extractor (printed LUNAS stamp date first, handwritten date field as fallback) and a **vendor name** extractor (heuristic read of the header lines at the top of the scan).
- **Dual Runtime & Astral `uv` Support**: Seamlessly executes via standard Python or Astral `uv`. Python scripts include PEP 723 inline dependency metadata (`# /// script`) for automatic zero-configuration dependency management under `uv run`.
- **Automated Setup & Winget Integration**: If neither Python nor `uv` is found, `setup_environment.bat` automatically offers to install Astral `uv` or Python via `winget` and refreshes the session PATH to resume work without manual terminal restarts.
- **Desktop Shortcut Creator (`create-shortcut.vbs`)**: Automatically creates Windows Desktop shortcuts upon environment setup (or manually on demand) for 1-click Downloads renaming or drag-and-drop custom folder renaming.
- **Preview-Locked Execution**: The dry run writes the exact mapping you're shown to a snapshot file (`logs/pending_mapping.json`). `execute_rename.py` renames from that snapshot instead of independently re-scanning — so what gets renamed is guaranteed to be what you approved, not a fresh guess that could differ if a file changed in between. The snapshot is refused if it's for a different folder or more than an hour old.
- **Low-Confidence Warnings**: When OCR is unavailable, finds no readable date, or can't confidently read a vendor header, the preview table flags that row with `⚠️` and a plain-language reason instead of silently guessing. Rows without a `⚠️` were read with confidence; rows with one are a fallback guess worth checking by hand.
- **Safe 2-Step Windows Renaming with Rollback**: Uses a temporary file (`.tmp_rename`) during renaming to support Windows case-only filename updates. If the second rename step fails partway (locked file, path too long, disk full), the file is rolled back to its original name instead of being left stuck as `<name>.pdf.tmp_rename`.
- **Filename Sanitization**: Strips characters illegal on Windows, trailing dots/spaces, Windows-reserved device names (`CON`, `PRN`, `NUL`, `COM1`...), and caps the filename stem length to stay under Windows' path-length limit.
- **Standardized Naming Convention**: Transfer receipts use:
  $$\text{\{YYYYMMDD\}} \quad \text{\{Receiver\}} \quad \text{\{Remark\}}.pdf$$
  *Example*: `20260728 Muhamad Fahmi Raihan Sul pembelian sayuran bale.pdf`
  Scanned bons use `bon_{vendor}_{YYYYMMDD}.pdf` (or `bon_{vendor}_{YYYYMMDD}-missed.pdf` if OCR date extraction fails and falls back to the scan date).
- **Title Case Normalization**: Converts raw receiver names (e.g. `DEDE MADIN` $\rightarrow$ `Dede Madin`).
- **Path Portability**: Supports `%USERPROFILE%\Downloads` and environment variable expansion across Windows environments.
- **Automatic Collision Resolution**: Detects duplicate proposed filenames or existing files on disk and automatically appends disambiguated suffixes like `(1)`, `(2)`, `(3)`.
- **Fail-Closed Batch Scripts**: If the dry run crashes or exits abnormally, the `.bat` runners abort instead of falling through to the rename confirmation prompt — you're never asked to approve a rename that was never actually previewed.
- **Daily Rotating Logs (`logs/YYYYMMDD.log`)**: Automatically logs dry runs, file renames, errors, and warnings into `logs/` with a **7-day retention policy**.

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

### 3. Before you approve
Check the preview table for any `⚠️` rows — those are fallback guesses (OCR unavailable, no date found, unclear vendor), not confirmed reads. Everything else was extracted with confidence.

---

## 📁 Project Structure

```
PDFrename/
├── dry_run_rename.py         # Parses PDFs/OCR, generates preview table, writes pending mapping snapshot
├── execute_rename.py         # Renames files from the pending snapshot, with rollback on partial failure
├── updater.py                # GitHub auto-update checker, staging downloader & deferred updater
├── logger.py                 # Daily rotating logger module (keeps 7 most recent log files)
├── rename_workflow.bat       # Windows runner defaulting to %USERPROFILE%\Downloads
├── run_workflow.bat          # Generic Windows runner (accepts custom target path)
├── setup_environment.bat     # Interactive environment & runtime installer (Python / uv / winget)
├── create-shortcut.vbs       # Generates Desktop shortcuts for 1-click execution and drag-and-drop
├── rename.md                 # Detailed SOP and naming specification document
├── INSTALL.md                # Installation and setup guide
├── .gitignore                # Git ignore configuration (ignores *.pdf, logs/, .venv/, cache)
└── logs/                     # Auto-generated daily log directory (YYYYMMDD.log) + pending_mapping.json
```

---

## 🪵 Logging System

All script operations (scans, counts, error logs, conflict resolution, renames) are logged automatically into `logs/YYYYMMDD.log`.
Old log files beyond the 7 most recent days are automatically pruned.

The dry run's approved-mapping snapshot also lives in `logs/pending_mapping.json`. It's created fresh by every dry run, consumed and deleted by the matching `execute_rename.py` call, and is refused (not silently re-derived) if it's stale or for a different target folder.

---

## 📋 Changelog

### `v1.6.0` (2026-09-07)
- **GitHub Repository Auto-Updater (`updater.py`)**: Added automated update checking against `https://github.com/nukie-git/PDFrename` on script start. When a newer commit is available, it downloads/stages the update and prompts the user to either [1] restart immediately with the updated code or [2] continue the current run and finalize the update automatically upon workflow completion.
- **Multi-Engine PDF Extraction (`fonttools`, `pdfplumber`, `pymupdf`)**: Added support for advanced font decoding and Word/Excel converted PDF parsing. `dry_run_rename.py` uses standard `pypdf` (accelerated by `fonttools` for CFF Type 1 fonts), falls back to dynamic `/ToUnicode` CMap synthesis via `fonttools` for embedded TrueType fonts, and falls back to `pymupdf` (complex fonts / paragraph layouts) and `pdfplumber` (table and gridline extraction for Excel conversions).
- **Singular Download Sequencing**: Optimized dependency installation across `setup_environment.bat`, `run_workflow.bat`, and `rename_workflow.bat`. Packages $< 5\text{ MB}$ (`pypdf`, `pillow`, `fonttools`) are downloaded together, while packages $\ge 5\text{ MB}$ (`pdfplumber`, `rapidocr-onnxruntime`, `pymupdf`) are installed singularly in separate sequential steps to protect host RAM and disk bandwidth.
- **PEP 723 Dependency Sync**: Synchronized all inline script metadata in `dry_run_rename.py` and `execute_rename.py` with `fonttools`, `pdfplumber`, and `pymupdf`.

### `v1.5.0` (2026-09-04)
- **Astral `uv` Runtime & PEP 723 Support**: Added automatic fallback to Astral `uv` if Python is not installed or not in `PATH`. Embeds PEP 723 inline script metadata (`# /// script`) in `dry_run_rename.py` and `execute_rename.py` for zero-setup execution and automatic dependency isolation.
- **Dedicated Environment Setup & Winget Auto-Installer (`setup_environment.bat`)**: Automatically prompts to install Astral `uv` or Python 3.12 via `winget` if neither is detected, refreshes the active session `PATH` from registry, and immediately resumes the workflow without needing to restart the terminal.
- **Desktop Shortcut Creator (`create-shortcut.vbs`)**: Added VBScript desktop shortcut generator that runs automatically upon environment setup (and can be run standalone) supporting 1-click Downloads renaming and drag-and-drop custom folder renaming onto the shortcut icon.
- **Batch Script Delegation**: Both `run_workflow.bat` and `rename_workflow.bat` seamlessly detect the available runtime (`python` vs `uv run`), dynamically delegate missing environment setup to `setup_environment.bat`, and resume execution cleanly.

### `v1.4.0` (2026-09-02)
- **Support for Mandiri "Multiple Transfer" Receipts**: Added support for Mandiri KOPRA *Multiple Transfer By Manual Input / File Upload* receipts. Expanded date parsing to include `Execution Date`, account extraction for `Credit Account Number`, and smart remark defaults (`Transfer`).

### `v1.3.3` (2026-09-01)
- **Expanded Date Regex for Mandiri Receipts**: Added support for 4-letter month abbreviations (e.g. `Sept` in `Creation Date 01 Sept 2026`) and added fallback to `Instruction Date` field.

### `v1.3.2` (2026-08-30)
- **Extensible Vendor Word Stripping**: Added `VENDOR_NAME_STRIP_WORDS = {'SABILULUNGAN'}` to drop non-essential vendor brand words from output filenames uniformly across OCR and default fallbacks.
- **Combined Low-Confidence Suffix (`-missed`)**: Triggered `-missed` filename suffix whenever either date OCR or vendor OCR produces a fallback warning.

### `v1.3.1` (2026-08-29)
- **`-missed` Filename Suffix**: Appended `-missed` to low-confidence fallback bon filenames so unconfirmed scans remain visually flagged after terminal session ends.

### `v1.3.0` (2026-08-29)
- **Preview-locked execution**: `execute_rename.py` now renames from the dry run's saved snapshot (`logs/pending_mapping.json`) instead of independently re-scanning the folder — closes a gap where the approved preview and the actual rename could silently diverge. Fixed a missing `import json` that had made the previous caching mechanism a no-op.
- **Rollback on partial rename failure**: a failed second rename step now restores the original filename instead of leaving the file stuck as `<name>.pdf.tmp_rename`.
- **Vendor OCR pass**: scanned bons now get a heuristic vendor name read from the header lines instead of a hardcoded vendor, with a warning flag when that read is inconclusive. Lines matching `Nama/Alamat Pemesanan` (the customer, never the vendor, on this receipt template) are excluded from vendor candidacy so a well-OCR'd customer name can't be mistaken for the vendor when the real vendor line lacks a `PT/CV/UD/TOKO/AGEN` marker.
- **Low-confidence warnings surfaced in the preview table**: OCR-unavailable, no-date-found, and inconclusive-vendor cases are now flagged with `⚠️` instead of silently producing a best-effort guess. The same flagging now also covers the Mandiri transfer-receipt path: a missing `Creation Date`, `Destination Account`, or `Remark` field is flagged, not just silently left as `UNKNOWN_DATE`/`UNKNOWN_RECEIVER`/`UNKNOWN_REMARK`.
- **Encrypted-PDF detection**: a password-protected PDF now reports a clear "password-protected/encrypted" error in the preview table instead of a generic exception message.
- **Date-fix scoping**: OCR digit/separator corrections (e.g. `108`→`08`) now apply only to the local text window around a candidate date match, not the whole OCR'd page — prevents unrelated text elsewhere on the receipt from being mangled.
- **Year cross-check**: a missing year in a matched date now falls back to a year found elsewhere in the OCR'd text (e.g. near the LUNAS stamp) before falling back to the current year, instead of a hardcoded year.
- **Filename sanitization**: added trailing dot/space stripping, Windows reserved-name handling, and a length cap on the filename stem.
- **Batch scripts fail closed**: `.bat` runners now abort on any dry-run exit code other than the expected 0/2/3, instead of falling through to the rename prompt after a crash.
- **Single owner for snapshot cleanup**: moved into `execute_rename.py`'s `finally` block; both `.bat` files no longer separately delete a cache file.

### `v1.2.0` (2026-08-29)
- **Multi-Layer OCR Date Parser**: Upgraded date extraction to prioritize printed LUNAS stamp dates (`10 AUG 2026`, `13 AUG 2026`, `19 AUG 2026`, `24 AUG 2026`) before falling back to handwritten date field parsing.
- **Regex Iteration Fix**: Switched to `re.finditer` across concatenated OCR text blocks to bypass address line false positives (`No.90 A Bandung`).

### `v1.1.1` (2026-08-06)
- **Automatic Cache File Cleanup**: Guaranteed purging of `.rename_cache.json` after execution, cancellation, or abort via Python `finally` handlers and batch exit traps.
- **Batch Script Syntax Fix**: Resolved Windows `cmd.exe` crash (`. was unexpected at this time`) by fixing unescaped parenthesis syntax in `if` blocks and enforcing CRLF line endings.

### `v1.1.0` (2026-08-06)
- **Scanned Bon OCR Feature**: Added support for image-based PDFs (`IMG_YearMonthDate_*`). Uses `rapidocr-onnxruntime` to extract handwritten/printed receipt dates inside the document.
- **Instant Execution Cache**: Added `.rename_cache.json` caching mechanism between dry run scan and file rename execution to eliminate redundant OCR processing.

### `v1.0.0` (2026-08-06)
- Initial release with Bank Mandiri KOPRA transfer receipt parsing, Title Case normalization, collision resolution, and daily rotating logs.

---

## 📜 License
[MIT License](LICENSE)

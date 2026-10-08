# PDFrename Workspace Guidelines

## 1. Project Overview & Architecture

**PDFrename** is an automated transaction receipt and bon scan renaming workflow tool for Windows. It processes:
1. **Bank Mandiri (KOPRA) Receipts**: Single Transfer and Multiple Transfer proofs.
2. **Scanned Bon Receipts**: Image-based scanned receipts matching `IMG_YYYYMMDD_*.pdf`.
3. **Tokopedia Order Receipts**: Platform purchase receipts.

### Key Files & Components
- `dry_run_rename.py`: PDF parser & OCR engine. Extracts metadata via multi-engine PDF parsing (`pypdf`, `fonttools`, `pymupdf`, `pdfplumber`) and `rapidocr-onnxruntime`, resolves collisions, prints visual markdown preview table, and saves the preview-locked snapshot to `logs/pending_mapping.json`.
- `execute_rename.py`: Renamer script executing strictly from `logs/pending_mapping.json` with temporary file renaming (`.tmp_rename`) and rollback protection on failure.
- `logger.py`: Daily rotating logger (`logs/YYYYMMDD.log`) with a 7-day retention policy.
- `updater.py`: GitHub auto-update checker and staging downloader for `nukie-git/PDFrename`.
- `setup_environment.bat`: Interactive environment installer & self-healing runtime setup (supports Python, Astral `uv`, and WinGet).
- `rename_workflow.bat`: Default Windows runner targeting `%USERPROFILE%\Downloads`.
- `run_workflow.bat`: General Windows runner supporting custom paths and Explorer drag-and-drop.
- `create-shortcut.vbs`: Windows desktop shortcut creator for 1-click execution.
- `PDFrename.zip`: Pre-packaged release archive maintaining root encapsulation (`PDFrename/...`).
- `.agents/rules/`: Agent rules for `rename_workflow.md` and `release_workflow.md`.

---

## 2. Operating Rules & Core Safety Guardrails

1. **NEVER Execute Renaming Without Approval**:
   - **Do NOT run `execute_rename.py` directly**.
   - Always run `dry_run_rename.py` first to generate the preview table and `logs/pending_mapping.json`.
   - Present the comparison table (`Original Filename` $\rightarrow$ `Proposed New Filename`) to the user.
   - Visually flag low-confidence rows (`⚠️`) and explain fallback reasons (OCR unavailable, no date found, fallback vendor).
   - Use the `ask_question` tool with options: `["Yes, proceed with renaming", "No, cancel"]`.
   - Only execute `execute_rename.py` if the user explicitly approves.
2. **Preview-Locked Execution**:
   - `execute_rename.py` renames strictly from `logs/pending_mapping.json`.
   - Snapshots are verified against the target directory and rejected if stale (> 1 hour old).
   - Never bypass or recompute mappings independently during execution.
3. **Safe Renaming & Rollback Guarantee**:
   - Renaming uses a two-step temporary rename (`.tmp_rename`) to support Windows case-only modifications safely.
   - If an error occurs during rename, automatic rollback restores original filenames.
4. **Scope Discipline**:
   - Do not make changes outside the requested task. Do not refactor, rename files, or bump dependencies unless requested.

---

## 3. Python Runtime & Dependency Management

### Dual Runtime Execution
Scripts support execution via both standard Python and Astral `uv`:
- **With `uv`**: `uv run dry_run_rename.py` / `uv run execute_rename.py` (PEP 723 inline dependency metadata `# /// script` is configured in scripts).
- **With standard Python**: `python dry_run_rename.py` / `python execute_rename.py`.
- Always prefer `uv` commands when operating in `uv`-managed environments.

### Dependencies
- **Core / Lightweight (< 5 MB)**: `pypdf`, `pillow`, `fonttools`.
- **Heavy / Sequential Installation (>= 5 MB)**: `rapidocr-onnxruntime`, `pdfplumber`, `pymupdf`.
- In setup scripts, install lightweight dependencies together, but install heavy packages sequentially to conserve host memory and disk bandwidth.

### Windows Script Guidelines
- Batch runners (`.bat`) must specify UTF-8 encoding (`chcp 65001 >nul`), enable delayed expansion where needed, handle drag-and-drop paths with quotes, and use Windows CRLF line endings.

---

## 4. Standardized Naming Conventions & Rules

1. **Bank Mandiri Transfer Receipts**:
   - Format: `YYYYMMDD {Receiver} {Remark}.pdf`
   - Example: `20260728 Muhamad Fahmi Raihan Sul pembelian sayuran bale.pdf`
   - Receiver names are normalized to Title Case.
2. **Scanned Bon Receipts (`IMG_YYYYMMDD_*`)**:
   - Format: `bon_{vendor}_{YYYYMMDD}.pdf`
   - Low confidence fallback: `bon_{vendor}_{YYYYMMDD}-missed.pdf`
   - Example: `bon_bentang_20260824.pdf`
3. **Tokopedia Platform Order Receipts**:
   - Format: `YYYYMMDD {Pembeli} {Info Produk}.pdf`
   - Example: `20260903 nukie Kotak Tempat wifi Router Rak wifi Rak Dinding Gantung Modem Wifi - Putih.pdf`
4. **Filename Sanitization**:
   - Illegal characters stripped: `\ / : * ? " < > |`
   - Trailing dots and spaces stripped.
   - Windows reserved device names protected (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
   - Filename stems capped to prevent Windows `MAX_PATH` issues.
   - Automatic collision resolution appends `(1)`, `(2)`, etc.

---

## 5. Logging & Snapshot Management

- **Daily Logs**: Written to `logs/YYYYMMDD.log` via `logger.py`. Log files older than 7 days are automatically pruned.
- **Pending Snapshot**: `logs/pending_mapping.json` is generated by `dry_run_rename.py` and consumed/deleted by `execute_rename.py`.
- **Git Hygiene**: `logs/`, `*.pdf`, `.venv/`, `.update_staging/`, and temporary caches are ignored via `.gitignore`.

---

## 6. Release & Packaging Workflow (`.agents/rules/release_workflow.md`)

When preparing a release or updating distribution packages:
1. **Pre-flight**: Confirm with the user before publishing tags or releases.
2. **Version Synchronization**: Update the version string across:
   - `README.md` (header & changelog)
   - `INSTALL.md` (header)
   - `rename.md` (header)
   - `setup_environment.bat` (banner)
   - Module docstrings in `dry_run_rename.py`, `execute_rename.py`, `logger.py`, `updater.py`
3. **Archive Packaging (`PDFrename.zip`)**:
   - Must encapsulate everything under a top-level `PDFrename/` directory.
   - Must include `.agents/rules/`, `LICENSE`, runners, scripts, and documentation.
4. **GitHub Releases**:
   - Tag format: `vX.Y.Z`
   - Release Asset Name: `PDFrename_[X.Y.Z].zip` (note: no `v` prefix in asset filename).

---

## 7. Documentation Integrity

- When updating any script, regex, parser, or runner, always synchronize project documentation (`README.md`, `INSTALL.md`, `rename.md`) and inline docstrings.
- Maintain comment clarity and keep all existing rules in sync with `.agents/rules/`.

# PDF Transaction Receipt & Bon Renaming Workflow SOP (v1.4.0)

This document defines the standard operating procedure for parsing and renaming PDF transaction receipts and scanned bon receipts within this project directory. Any AI assistant or conversation should read and follow this guide when triggered.

---

## 1. Trigger
- **Command**: Triggered when the user types `"start"` or requests PDF file renaming.

---

## 2. Naming Convention Templates

There are two document types, each with its own template.

### 2a. Mandiri transfer receipts (text-based PDF)

$$\text{\{year\}\{month\}\{date\}} \quad \text{\{receiver\}} \quad \text{\{remark\}}.pdf$$

Example output: `20260721 Dede Madin pembelian salak bale.pdf`

| Field | Source Field in Document | Formatting & Normalization Rules | Example Input $\rightarrow$ Output |
| :--- | :--- | :--- | :--- |
| `{year}{month}{date}` | `Creation Date` | `YYYYMMDD` 8-digit format. | `Jul 21, 2026 ...` $\rightarrow$ `20260721` |
| `{receiver}` | `Destination Account` | Account number stripped. Normalized to **Title Case**. | `1300028332230 DEDE MADIN` $\rightarrow$ `Dede Madin` |
| `{remark}` | `Remark` | Exact text from remark field. | `pembelian salak bale` $\rightarrow$ `pembelian salak bale` |

All fields are sanitized for invalid OS filename characters (`\ / : * ? " < > \|`), trailing dots/spaces, and Windows-reserved device names (`CON`, `PRN`, `NUL`, `COM1`...), and truncated if the combined stem would exceed a safe length.

### 2b. Scanned bon receipts (image-based PDF, filename matches `IMG_YYYYMMDD_*`)

$$\text{bon\_\{vendor\}\_\{year\}\{month\}\{date\}}.pdf$$

Example output: `bon_bentang_20260824.pdf` (or `bon_bentang_20260829-missed.pdf` when OCR date extraction is missed/fallback)

| Field | Source | Extraction Order | Notes |
| :--- | :--- | :--- | :--- |
| `{vendor}` | OCR of the header lines at the top of the scan | Heuristic: prefer a header line containing `PT`/`CV`/`UD`/`TOKO`/`AGEN`; otherwise the topmost plausible text line | Falls back to a default vendor name with a `⚠️` warning if OCR is unavailable or the header can't be read confidently |
| `{year}{month}{date}` | 1. Any text layer on the page, then 2. OCR: printed LUNAS stamp date, then 3. OCR: handwritten date field, then 4. the date embedded in the scan's own filename | First successful step wins | Falls back to the filename's own date (the scan date, **not** the transaction date) with a `⚠️` warning if steps 1–3 all fail |

---

## 3. Strict Workflow

> [!IMPORTANT]
> **CRITICAL RULE**: Do **NOT** rename any files without explicit user approval. Always present the preview table first and wait for user confirmation.

1. **Scan PDF Files**: Find all `.pdf` files inside the target folder (e.g. `%USERPROFILE%\Downloads` or current workspace directory).
2. **Filter & Parse Document Data**:
   - Files matching `IMG_YYYYMMDD_*.pdf` are treated as scanned bons (see §2b).
   - All other files are checked for `"Single Transfer To Other Bank"` or `"Single Transfer To Mandiri"` (case-insensitive); if absent, the file is skipped. Otherwise extract `Creation Date`, `Destination Account`, and `Remark` using `pypdf` (see §2a).
3. **Generate Visual Dry Run / Preview**:
   Output a clear markdown preview table showing original vs proposed new filenames side-by-side.
   - If proposed filenames conflict with existing files or duplicate receipts, automatically append numbered suffixes like `(1)`, `(2)`, `(3)` to resolve collisions and display a warning banner.
   - If any row was built from a fallback guess (OCR unavailable, no date found, inconclusive vendor read), mark that row with `⚠️` and print the specific reason beneath it. **Rows with a `⚠️` should be checked by hand before approving** — they were not confidently read.
   - Save the exact mapping shown to `logs/pending_mapping.json`. This is what gets executed — not a fresh re-scan — so it must be re-generated (by re-running the dry run) if the target folder's contents change before you approve.
4. **Prompt User for Action**:
   - Use the `ask_question` tool to present the user with interactive buttons (`Yes, proceed with renaming` / `No, cancel`) to capture their approval. If conflicts or `⚠️` warnings were detected, explicitly call them out in the prompt.
5. **Execute Renaming**:
   - Upon user selection of the "Yes" option, run `execute_rename.py`, which renames strictly from `logs/pending_mapping.json`. It refuses to proceed (rather than silently re-scanning) if that snapshot is missing, is for a different folder, or is more than an hour old — re-run the dry run in that case.
   - On Windows, uses a two-step temporary rename (`.tmp_rename`) so case-only changes (like `DEDE MADIN` to `Dede Madin`) apply correctly. If the second step of that rename fails, the file is rolled back to its original name rather than left as `<name>.pdf.tmp_rename`.
   - The snapshot is deleted after execution completes (success or failure) so a stale mapping can't be reused by accident.

---

## 4. Helper Scripts Reference

- [dry_run_rename.py](dry_run_rename.py): Parses all PDFs in the directory (including OCR for scanned bons), outputs a preview table with warnings/collision resolution, and writes `logs/pending_mapping.json`.
- [execute_rename.py](execute_rename.py): Renames files strictly from `logs/pending_mapping.json`, with rollback on partial rename failure.
- [logger.py](logger.py): Logs operation activities to `logs/YYYYMMDD.log` with a 7-day daily rotation policy.

---

*Note: Keep this file updated whenever the renaming template, normalization rules, or workflow steps change.*

# PDF Transaction Receipt & Bon Renaming Workflow SOP (v1.2.0)

This document defines the standard operating procedure for parsing and renaming PDF transaction receipts and scanned bon receipts within this project directory. Any AI assistant or conversation should read and follow this guide when triggered.

---

## 1. Trigger
- **Command**: Triggered when the user types `"start"` or requests PDF file renaming.

---

## 2. Naming Convention Template

$$\text{\{year\}\{month\}\{date\}} \quad \text{\{receiver\}} \quad \text{\{remark\}}.pdf$$

Example output: `20260721 Dede Madin pembelian salak bale.pdf`

### Field Rules:
| Field | Source Field in Document | Formatting & Normalization Rules | Example Input $\rightarrow$ Output |
| :--- | :--- | :--- | :--- |
| `{year}{month}{date}` | `Creation Date` | `YYYYMMDD` 8-digit format. | `Jul 21, 2026 ...` $\rightarrow$ `20260721` |
| `{receiver}` | `Destination Account` | Account number stripped. Normalized to **Title Case** (uppercase first letter of each word). | `1300028332230 DEDE MADIN` $\rightarrow$ `Dede Madin` |
| `{remark}` | `Remark` | Exact text from remark field. Sanitized for invalid OS filename characters (`\ / : * ? " < > \|`). | `pembelian salak bale` $\rightarrow$ `pembelian salak bale` |

---

## 3. Strict 5-Step Workflow

> [!IMPORTANT]
> **CRITICAL RULE**: Do **NOT** rename any files without explicit user approval. Always present the preview table first and wait for user confirmation.

1. **Scan PDF Files**: Find all `.pdf` files inside the target folder (e.g. `%USERPROFILE%\Downloads` or current workspace directory).
2. **Filter & Parse Document Data**: Verify that each PDF contains single transfer indicators (`"Single Transfer To Other Bank"` or `"Single Transfer To Mandiri"`, case-insensitive). If it doesn't, skip the file. Otherwise, extract `Creation Date`, `Destination Account`, and `Remark` using `pypdf`.
3. **Generate Visual Dry Run / Preview**:
   Output a clear markdown preview table showing original vs proposed new filenames side-by-side. If proposed filenames conflict with existing files or duplicate receipts, automatically append numbered suffixes like `(1)`, `(2)`, `(3)` to resolve collisions and display a warning.
4. **Prompt User for Action**:
   - Use the `ask_question` tool to present the user with interactive buttons (`Yes, proceed with renaming` / `No, cancel`) to capture their approval. If conflicts were detected, explicitly prompt the user regarding collision resolution.
5. **Execute Renaming**:
   - Upon user selection of the "Yes" option, rename the files. Note: On Windows, use a two-step temporary rename (`.tmp_rename`) to ensure case-only changes (like `DEDE MADIN` to `Dede Madin`) apply correctly.

---

## 4. Helper Scripts Reference

- [dry_run_rename.py](dry_run_rename.py): Parses all PDFs in the directory and outputs a preview table with Title Case normalization and collision resolution.
- [execute_rename.py](execute_rename.py): Performs the actual safe file renaming after user approval.
- [logger.py](logger.py): Logs operation activities to `logs/YYYYMMDD.log` with a 7-day daily rotation policy.

---

*Note: Keep this file updated whenever the renaming template, normalization rules, or workflow steps change.*

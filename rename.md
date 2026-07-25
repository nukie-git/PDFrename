# PDF Transaction Receipt Renaming Workflow

This document defines the standard operating procedure for parsing and renaming PDF transaction receipts within this project directory. Any AI assistant or conversation should read and follow this guide when triggered.

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

1. **Scan PDF Files**: Find all `.pdf` files inside the project folder (`C:\Users\nukie\apps\rename`).
2. **Filter & Parse Document Data**: Verify that each PDF contains either `"Transaction Status Single Transfer to Other Bank"` or `"Transaction Status Single Transfer to Mandiri"`. If it doesn't, skip the file. Otherwise, extract `Creation Date`, `Destination Account`, and `Remark` using `pypdf`.
3. **Generate Visual Dry Run / Preview**:
   Output a clear markdown preview table showing original vs proposed new filenames side-by-side directly in the chat message response.
4. **Prompt User for Action**:
   - Use the `ask_question` tool to present the user with interactive buttons (`Yes, proceed with renaming` / `No, cancel`) to capture their approval.
5. **Execute Renaming**:
   - Upon user selection of the "Yes" option, rename the files. Note: On Windows, use a two-step temporary rename (`.tmp_rename`) to ensure case-only changes (like `DEDE MADIN` to `Dede Madin`) apply correctly.

---

## 4. Helper Scripts Reference

- [dry_run_rename.py](file:///C:/Users/nukie/apps/rename/dry_run_rename.py): Parses all PDFs in the directory and outputs a preview table with Title Case normalization.
- [execute_rename.py](file:///C:/Users/nukie/apps/rename/execute_rename.py): Performs the actual safe file renaming after user approval.

---

*Note: Keep this file updated whenever the renaming template, normalization rules, or workflow steps change.*

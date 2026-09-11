# PDF Receipt Renaming Workflow Rule

This rule ensures that any AI agent operating in this workspace correctly executes the PDF transaction receipt renaming workflow.

## Activation
- **Trigger**: When the user says `"start"` or requests PDF receipt renaming.
- **Rule Type**: Model Decision / Always On for PDF renaming requests.

---

## Instructions

If the user triggers this workflow (e.g. by typing `"start"`):

1. **Do NOT run execute_rename.py first**.
2. **Execute a Dry Run / Preview**:
   - Run [dry_run_rename.py](dry_run_rename.py) (using `python dry_run_rename.py` or `uv run dry_run_rename.py`) to get the preview mapping.
   - The script will automatically detect Bank Mandiri transfer receipts, scanned bon receipts matching `IMG_YYYYMMDD_*.pdf`, and Tokopedia platform order receipts (`TOKOPEDIA`). Any unsupported PDF files are skipped automatically.
   - Output the preview table directly in the chat message window so that the user can visually see the comparison between **Original Filename** and **Proposed New Filename**.
   - If any row is marked `⚠️`, call it out explicitly to the user before asking for approval — it means that field was a fallback guess (OCR unavailable, no date found, unclear vendor), not a confirmed read.
3. **Wait for Explicit Approval**:
   - Use the `ask_question` tool to prompt the user with interactive buttons.
   - Set the question to: *"Would you like to proceed with renaming the PDF files according to the preview?"*
   - Provide the options: `["Yes, proceed with renaming", "No, cancel"]`.
4. **Execute Renaming**:
   - Only run [execute_rename.py](execute_rename.py) if the user selects the `"Yes, proceed with renaming"` option.

---

## Mandatory Documentation & Versioning Policy

> [!IMPORTANT]
> **ALWAYS ADD & UPDATE DOCUMENTATION**: Whenever any script, regex pattern, template, runner, or workflow logic is created or significantly modified:
> 1. **Inline Code Documentation**: Update module docstrings, function docstrings, and inline comments in Python scripts (`dry_run_rename.py`, `execute_rename.py`, `logger.py`) and Windows batch / VBScript runners (`run_workflow.bat`, `rename_workflow.bat`, `setup_environment.bat`, `create-shortcut.vbs`).
> 2. **Project Documentation**: Update `README.md`, `rename.md`, and `INSTALL.md` with the new version number, changelog entries, and updated technical specifications.
> 3. **Workflow Archive & Releases**: Re-pack `PDFrename.zip` under the `PDFrename/` root directory encapsulation with `LICENSE`, and manage GitHub releases according to [.agents/rules/release_workflow.md](release_workflow.md).

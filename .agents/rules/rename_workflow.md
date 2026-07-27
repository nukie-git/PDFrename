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
   - Run [dry_run_rename.py](dry_run_rename.py) to get the preview mapping.
   - The script will automatically filter out any PDFs that do not contain `"Single Transfer To Other Bank"` or `"Single Transfer To Mandiri"`.
   - Output the preview table directly in the chat message window so that the user can visually see the comparison between **Original Filename** and **Proposed New Filename**.
3. **Wait for Explicit Approval**:
   - Use the `ask_question` tool to prompt the user with interactive buttons.
   - Set the question to: *"Would you like to proceed with renaming the PDF files according to the preview?"*
   - Provide the options: `["Yes, proceed with renaming", "No, cancel"]`.
4. **Execute Renaming**:
   - Only run [execute_rename.py](execute_rename.py) if the user selects the `"Yes, proceed with renaming"` option.

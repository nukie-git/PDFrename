# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pypdf",
#     "pillow",
#     "rapidocr-onnxruntime",
#     "fonttools",
#     "pdfplumber",
#     "pymupdf",
# ]
# ///
"""execute_rename.py (PDFrename v1.6.0)

Safe file renamer executing strictly from the preview-locked snapshot (logs/pending_mapping.json)
generated during the last dry run. Supports execution via Python or Astral uv.

Enforces directory verification, maximum snapshot age validation (1 hour), Windows 2-step
case-only temporary renaming (.tmp_rename), automatic rollback on partial rename failure,
and single-owner snapshot cleanup upon completion.
"""

import os
import json
from datetime import datetime, timedelta

from dry_run_rename import get_pending_path
from logger import log
from updater import finalize_deferred_update

MAX_SNAPSHOT_AGE = timedelta(hours=1)


def load_pending_mapping(directory):
    """Load the exact mapping the user was shown in the last dry run, instead of
    silently recomputing a fresh (possibly different) one. Refuses to proceed if no
    snapshot exists, it's for a different directory, or it's stale."""
    pending_path = get_pending_path()
    if not os.path.exists(pending_path):
        return None, "No dry-run preview found. Run the dry run first and approve its output."

    try:
        with open(pending_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except Exception as e:
        return None, f"Could not read dry-run snapshot: {e}"

    target_abs = os.path.abspath(os.path.expandvars(os.path.expanduser(directory)))
    if payload.get('directory') != target_abs:
        return None, (
            f"Dry-run snapshot was for '{payload.get('directory')}', "
            f"not '{target_abs}'. Re-run the dry run on this folder first."
        )

    try:
        generated_at = datetime.fromisoformat(payload['generated_at'])
    except Exception:
        return None, "Dry-run snapshot is malformed. Re-run the dry run."

    if datetime.now() - generated_at > MAX_SNAPSHOT_AGE:
        return None, "Dry-run snapshot is stale (>1 hour old). Re-run the dry run for a fresh preview."

    return payload['mapping'], None


def rename_files(directory='.'):
    directory = os.path.expandvars(os.path.expanduser(directory))
    log(f"Starting execute rename on directory: {directory}", "INFO")

    mapping, err = load_pending_mapping(directory)
    if err:
        print(f"[ABORTED] {err}")
        log(f"Execute aborted: {err}", "ERROR")
        return

    renamed_count = 0

    print("--- EXECUTING RENAME ---")
    try:
        for item in mapping:
            if 'error' in item:
                msg = f"[SKIP] {item['original']}: {item['error']}"
                print(msg)
                log(msg, "ERROR")
                continue

            old_path = item['full_original']
            new_path = item['full_new']

            if item['original'] == item['new']:
                msg = f"[NO CHANGE] {item['original']}"
                print(msg)
                log(msg, "INFO")
                continue

            if not os.path.exists(old_path):
                msg = f"[SKIP] {item['original']}: file no longer exists (moved/renamed since preview)"
                print(msg)
                log(msg, "ERROR")
                continue

            if os.path.exists(new_path):
                msg = f"[SKIP] {item['original']}: target '{item['new']}' already exists (state changed since preview)"
                print(msg)
                log(msg, "ERROR")
                continue

            temp_path = old_path + ".tmp_rename"
            try:
                # On Windows, renaming a file to a case-only change requires a 2-step rename
                os.rename(old_path, temp_path)
            except Exception as e:
                msg = f"[ERROR] Could not rename {item['original']}: {e}"
                print(msg)
                log(msg, "ERROR")
                continue

            try:
                os.rename(temp_path, new_path)
                msg = f"[RENAMED] {item['original']} -> {item['new']}"
                print(msg)
                log(msg, "SUCCESS")
                renamed_count += 1
            except Exception as e:
                # Second step failed - roll back to the original filename rather than
                # leaving the file stuck as '<name>.pdf.tmp_rename' and invisible to
                # future scans.
                try:
                    os.rename(temp_path, old_path)
                    msg = f"[ERROR] Could not rename {item['original']} -> {item['new']}: {e}. Rolled back to original name."
                except Exception as rollback_err:
                    msg = (
                        f"[CRITICAL] Could not rename {item['original']} -> {item['new']}: {e}. "
                        f"Rollback also failed: {rollback_err}. "
                        f"File may be stuck at '{os.path.basename(temp_path)}' - check manually."
                    )
                print(msg)
                log(msg, "ERROR")

        summary_msg = f"Successfully renamed {renamed_count} files."
        print(f"\n{summary_msg}")
        log(summary_msg, "INFO")
    finally:
        # Single owner of pending-snapshot cleanup (see rename_workflow.bat / run_workflow.bat -
        # they no longer delete it themselves).
        pending_path = get_pending_path()
        if os.path.exists(pending_path):
            try:
                os.remove(pending_path)
                log(f"Cleaned up pending mapping snapshot: {pending_path}", "INFO")
            except Exception as e:
                log(f"Failed to remove pending mapping snapshot ({pending_path}): {e}", "WARNING")

        # Finalize any deferred GitHub updates scheduled with Option [2]
        finalize_deferred_update()


if __name__ == '__main__':
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    rename_files(target_dir)

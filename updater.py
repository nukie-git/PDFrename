"""updater.py (PDFrename)

GitHub repository auto-update checker and installer for PDFrename.
Checks remote GitHub repository (https://github.com/nukie-git/PDFrename) on script start.
If updates are available:
- Downloads and stages the update (via git fetch or GitHub API/raw downloads).
- Prompts user to either:
    [1] Restart script now with update, or
    [2] Continue first & update after current process is finished.
- Finalizes deferred updates cleanly upon workflow completion.
"""

import os
import sys
import json
import shutil
import urllib.request
import subprocess
from datetime import datetime

from logger import log, get_logs_dir

GITHUB_OWNER = "nukie-git"
GITHUB_REPO = "PDFrename"
GITHUB_BRANCH = "main"
GITHUB_API_COMMITS = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
UPDATE_STAGING_DIR = os.path.join(PROJECT_DIR, ".update_staging")
PENDING_UPDATE_FILE = "pending_update.json"
VERSION_FILE = os.path.join(PROJECT_DIR, ".version")

CORE_UPDATE_FILES = [
    "dry_run_rename.py",
    "execute_rename.py",
    "logger.py",
    "updater.py",
    "setup_environment.bat",
    "run_workflow.bat",
    "rename_workflow.bat",
    "create-shortcut.vbs",
    "rename.md",
    "README.md",
    "INSTALL.md",
]


def get_pending_update_path():
    return os.path.join(get_logs_dir(), PENDING_UPDATE_FILE)


def is_git_repo():
    return os.path.isdir(os.path.join(PROJECT_DIR, ".git"))


def get_local_commit():
    """Retrieve current local commit SHA, either via git or saved .version file."""
    if is_git_repo():
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                sha = f.read().strip()
                if sha:
                    return sha
        except Exception:
            pass

    return None


def get_remote_commit():
    """Check remote commit SHA from GitHub via git ls-remote or GitHub API."""
    # 1. Try git ls-remote if git is available
    if is_git_repo():
        try:
            res = subprocess.run(
                ["git", "ls-remote", "origin", f"refs/heads/{GITHUB_BRANCH}"],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=4,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split()
                if parts:
                    return parts[0]
        except Exception:
            pass

    # 2. Fallback to GitHub REST API with 3-second timeout
    try:
        req = urllib.request.Request(
            GITHUB_API_COMMITS,
            headers={"User-Agent": "PDFrename-AutoUpdater", "Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            if "sha" in data:
                return data["sha"]
    except Exception as e:
        log(f"Remote commit check via GitHub API skipped/failed: {e}", "DEBUG")

    return None


def stage_update_files(remote_sha):
    """Download updated files from GitHub raw to .update_staging/."""
    try:
        if os.path.exists(UPDATE_STAGING_DIR):
            shutil.rmtree(UPDATE_STAGING_DIR, ignore_errors=True)
        os.makedirs(UPDATE_STAGING_DIR, exist_ok=True)

        for filename in CORE_UPDATE_FILES:
            url = f"{GITHUB_RAW_BASE}/{filename}"
            dest_path = os.path.join(UPDATE_STAGING_DIR, filename)
            parent = os.path.dirname(dest_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "PDFrename-AutoUpdater"})
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    with open(dest_path, "wb") as out_f:
                        out_f.write(resp.read())
            except Exception as fe:
                log(f"Could not download '{filename}' during staging: {fe}", "DEBUG")

        # Save staged version marker
        with open(os.path.join(UPDATE_STAGING_DIR, ".version"), "w", encoding="utf-8") as f:
            f.write(remote_sha)

        return True
    except Exception as e:
        log(f"Failed to stage update files: {e}", "WARNING")
        if os.path.exists(UPDATE_STAGING_DIR):
            shutil.rmtree(UPDATE_STAGING_DIR, ignore_errors=True)
        return False


def check_and_download_update():
    """Check for updates on GitHub and download/stage them if found.
    Returns update_info dict if update is ready, or None otherwise.
    """
    local_sha = get_local_commit()
    remote_sha = get_remote_commit()

    if not remote_sha:
        return None

    if local_sha and local_sha == remote_sha:
        return None  # Up to date

    log(f"Update detected on GitHub: local={local_sha[:7] if local_sha else 'unknown'} -> remote={remote_sha[:7]}", "INFO")
    print(f"\n[UPDATE CHECK] Update found on GitHub ({remote_sha[:7]}). Downloading update...")

    # Attempt git fetch first if in a git repo
    method = "files"
    if is_git_repo():
        try:
            fetch_res = subprocess.run(
                ["git", "fetch", "origin", GITHUB_BRANCH],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if fetch_res.returncode == 0:
                method = "git"
                log("Git fetch completed successfully for update staging.", "INFO")
        except Exception as ge:
            log(f"Git fetch failed, falling back to direct file download: {ge}", "DEBUG")

    # If not git or git fetch failed, stage via HTTP download
    if method == "files":
        staged = stage_update_files(remote_sha)
        if not staged:
            log("Failed to stage update files from GitHub.", "WARNING")
            return None

    print("[SUCCESS] Update downloaded and prepared successfully.")
    return {
        "local_sha": local_sha,
        "remote_sha": remote_sha,
        "method": method,
    }


def prompt_update_choice(current_sha, new_sha):
    """Prompt the user whether to restart now or defer until the current run finishes."""
    curr_disp = current_sha[:7] if current_sha else "local"
    new_disp = new_sha[:7] if new_sha else "latest"

    print("\n" + "=" * 55)
    print("  [UPDATE READY] A new version of PDFrename is available!")
    print(f"  Version: {curr_disp}  ->  {new_disp}")
    print("=" * 55)
    print("The updated scripts have been downloaded.\n")
    print("Choose an option:")
    print("  [1] Restart script now with update")
    print("  [2] Continue first & update after current process is finished")
    print()

    try:
        choice = input("Enter choice (1 or 2, default 2): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "2"

    return "1" if choice == "1" else "2"


def apply_staged_update(update_info=None):
    """Apply the downloaded update to the project directory."""
    if not update_info:
        update_info = {}
    method = update_info.get("method")
    remote_sha = update_info.get("remote_sha", "")

    try:
        # If method was git, pull/merge changes
        if method == "git" and is_git_repo():
            try:
                # Check for dirty working tree
                status_res = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=PROJECT_DIR,
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                has_local_changes = bool(status_res.stdout.strip())
                if has_local_changes:
                    subprocess.run(["git", "stash"], cwd=PROJECT_DIR, capture_output=True, timeout=5)

                merge_res = subprocess.run(
                    ["git", "merge", f"origin/{GITHUB_BRANCH}"],
                    cwd=PROJECT_DIR,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if has_local_changes:
                    subprocess.run(["git", "stash", "pop"], cwd=PROJECT_DIR, capture_output=True, timeout=5)

                if merge_res.returncode == 0:
                    log(f"Git merge succeeded for commit {remote_sha[:7]}.", "INFO")
                    return True
            except Exception as ge:
                log(f"Git merge failed ({ge}), falling back to file copy if staged.", "WARNING")

        # Files copy method (from .update_staging/ or direct)
        if os.path.isdir(UPDATE_STAGING_DIR):
            for root, dirs, files in os.walk(UPDATE_STAGING_DIR):
                rel_root = os.path.relpath(root, UPDATE_STAGING_DIR)
                target_root = PROJECT_DIR if rel_root == "." else os.path.join(PROJECT_DIR, rel_root)
                os.makedirs(target_root, exist_ok=True)
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(target_root, file)
                    shutil.copy2(src_file, dst_file)

            shutil.rmtree(UPDATE_STAGING_DIR, ignore_errors=True)
            if remote_sha:
                try:
                    with open(VERSION_FILE, "w", encoding="utf-8") as f:
                        f.write(remote_sha)
                except Exception:
                    pass
            log(f"Staged files copied successfully for commit {remote_sha[:7]}.", "INFO")
            return True

        return False
    except Exception as e:
        log(f"Error applying update: {e}", "ERROR")
        return False


def restart_script():
    """Restart current Python process with original command line arguments."""
    log("Restarting process with updated scripts...", "INFO")
    print("\n[RESTARTING] Launching updated PDFrename workflow...")
    try:
        sys.exit(subprocess.call([sys.executable] + sys.argv))
    except Exception as e:
        log(f"Failed to restart script: {e}", "ERROR")
        print(f"[ERROR] Could not restart automatically: {e}. Please re-run the script.")
        sys.exit(0)


def save_deferred_update(update_info):
    """Save pending update information so it can be finalized after workflow finishes."""
    payload = {
        "status": "pending",
        "update_info": update_info,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        with open(get_pending_update_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        log(f"Saved deferred update state: commit {update_info.get('remote_sha', '')[:7]}", "INFO")
    except Exception as e:
        log(f"Failed to write deferred update state: {e}", "WARNING")


def finalize_deferred_update():
    """Apply any deferred update if one was scheduled by option [2]."""
    pending_path = get_pending_update_path()
    if not os.path.exists(pending_path):
        return False

    try:
        with open(pending_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        log(f"Could not read pending update snapshot: {e}", "WARNING")
        return False

    if payload.get("status") != "pending":
        return False

    update_info = payload.get("update_info", {})
    remote_sha = update_info.get("remote_sha", "")
    print("\n" + "=" * 55)
    print("  [FINALIZING UPDATE] Applying pending GitHub update...")
    print("=" * 55)
    log(f"Applying deferred update ({remote_sha[:7]})...", "INFO")

    success = apply_staged_update(update_info)
    try:
        os.remove(pending_path)
    except Exception:
        pass

    if success:
        print(f"[SUCCESS] PDFrename has been successfully updated to latest version ({remote_sha[:7]}).\n")
        log(f"Deferred update finalized successfully ({remote_sha[:7]}).", "INFO")
    else:
        print("[WARNING] Could not apply deferred update automatically. You can update manually via git pull.\n")
        log("Deferred update could not be applied cleanly.", "WARNING")

    return success


def check_and_prompt_update():
    """Entry point called on script start. Checks GitHub, downloads if new, and prompts."""
    try:
        update_info = check_and_download_update()
        if not update_info:
            return  # No update or check silently timed out

        choice = prompt_update_choice(
            update_info.get("local_sha", ""),
            update_info.get("remote_sha", ""),
        )

        if choice == "1":
            applied = apply_staged_update(update_info)
            if applied:
                restart_script()
            else:
                log("Update application failed, continuing with current script.", "WARNING")
        else:
            save_deferred_update(update_info)
            print("[INFO] Continuing current run. Update will be applied after workflow finishes.\n")
    except Exception as e:
        log(f"Auto-update check encountered an error: {e}", "DEBUG")

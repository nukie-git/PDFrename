# Release Management & Distribution Workflow Rule

This rule defines the mandatory Standard Operating Procedure (SOP) for publishing, updating, packaging, and releasing PDFrename on GitHub.

## Activation
- **Trigger**: When the user requests to publish, update, check, repack, or plan releases for PDFrename.
- **Rule Type**: Always On / Model Decision.

---

## Strict Release Workflow SOP

Whenever a new version or release is prepared:

### 1. Pre-Flight Check & User Confirmation
- Audit upstream commits and tags via `git fetch` and `git ls-remote --tags origin`.
- Always present the proposed release plan, version number, commit target, and changelog summary to the user.
- If multiple release strategies or options exist, ask the user for confirmation and option selection before modifying remote tags or publishing releases.

### 2. Version Bump & Documentation Integrity
Ensure the version string (e.g. `vX.Y.Z`) is updated consistently across:
- [README.md](README.md) (Title header and `## 📋 Changelog` entry)
- [INSTALL.md](INSTALL.md) (Header title)
- [rename.md](rename.md) (Header title)
- [setup_environment.bat](setup_environment.bat) (Header banner)
- Module docstrings in Python scripts (`dry_run_rename.py`, `execute_rename.py`, `logger.py`, `updater.py`)
- Batch runners: ensure `echo   © nukie 2026`, UTF-8 code page `chcp 65001 >nul`, and strict Windows CRLF (`\r\n`) line endings.

### 3. Workflow Archive Packaging Flow
The release archive MUST follow the root-directory encapsulation structure:
- **Tracked Archive Filename**: `pdf_rename_workflow.zip`
- **Root Directory Inside Archive**: All files must be nested inside a single top-level `PDFrename/` directory so unzipping produces a clean folder rather than scattering files:
  ```
  PDFrename/
  ├── .agents/rules/rename_workflow.md
  ├── .agents/rules/release_workflow.md
  ├── .gitignore
  ├── create-shortcut.vbs
  ├── dry_run_rename.py
  ├── execute_rename.py
  ├── INSTALL.md
  ├── LICENSE
  ├── logger.py
  ├── README.md
  ├── rename.md
  ├── rename_workflow.bat
  ├── run_workflow.bat
  ├── setup_environment.bat
  └── updater.py
  ```
- Explicit directory entries for `PDFrename/`, `PDFrename/.agents/`, `PDFrename/.agents/rules/`.
- `LICENSE` MUST always be included in the package.

### 4. Git Commit & Annotated Tagging
- Commit the repacked `pdf_rename_workflow.zip` and all code/documentation updates to `main`.
- Push commit to `origin/main`.
- Create an annotated git tag pointing to the exact release commit:
  ```bash
  git tag -a vX.Y.Z <commit_sha> -m "vX.Y.Z - <Release Title>"
  git push origin vX.Y.Z
  ```

### 5. GitHub Release & Asset Upload
- Create or update GitHub Release using GitHub REST API:
  - `tag_name`: `vX.Y.Z`
  - `name`: `vX.Y.Z - <Feature Summary Title>`
  - `body`: Markdown release notes matching the repository changelog.
- **Asset Naming Convention**:
  - The uploaded asset MUST be named:
    $$\text{PDFrename\_[VersionNumber].zip}$$
    where `[VersionNumber]` is the semantic version number **without the `v` prefix** (e.g. `PDFrename_1.6.0.zip`, `PDFrename_1.5.0.zip`).
  - Upload via `POST https://uploads.github.com/repos/nukie-git/PDFrename/releases/{id}/assets?name=PDFrename_{VersionNumber}.zip`.

### 6. Verification
- Query GitHub Releases API to confirm release status, asset presence, and valid download URLs.
- Verify archive integrity by downloading and testing table of contents extraction.

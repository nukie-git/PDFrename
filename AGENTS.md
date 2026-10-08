# Workspace Guidelines

## 0. Operating rules (read first, obey throughout)

1. After every task run `cd app && uv run pytest -q`. If anything fails, **stop**, fix, and re-run. Never skip, xfail or delete a test to get green.
2. Do not change behavior outside the task. No refactors, no renames, no dependency upgrades unless a task says so.
3. Do not invent data. Where a value must come from the owner (unit conversion factors, HET policy), generate a file for the human to fill.

## Python Environment & Package Management
- Always use `uv` instead of standard `python`, `pip`, or `venv` commands for all Python tasks in this workspace.
- Use `uv run` for executing Python scripts.
- Use `uv venv` for creating virtual environments.
- Use `uv add` or `uv pip install` for managing packages.
- Use `uv python install` for managing Python versions.

## Startup Script & Service Boot Ordering (`master-boot-launcher.ps1`)
When adding, modifying, or reordering applications in `master-boot-launcher.ps1`, you MUST ALWAYS strictly follow and preserve the **Tiered Gateway-First Architecture**:

1. **Pre-Flight (Foundation)**: Stale sentinel flag scrubbing (`*.flag`), path healing, Tailscale MagicDNS host determination, Caddyfile template generation, and Caddy Root CA trust.
2. **Tier 0 (Gateway)**: **Caddy Reverse Proxy (`:80` / `:443`)** &mdash; MUST ALWAYS launch first so web endpoints and the Media Portal are immediately reachable upon boot.
3. **Tier 1 (Core Portal & APIs)**: **Admin Service Backend (`:8085`)** and **System Update Monitor (`:8084`)** &mdash; Powers `/admin-api/health` probes and status badges.
4. **Tier 2 (Content & Files)**: **Filebrowser (`:8082`)**, **FileBrowser Quantum (`:8082`)**, **Calibre Content Server (`:8081`)**, and **Calibre-Web (`:8083`)**.
5. **Tier 3 (Telemetry & Heavy Media Engines)**: **Jellyfin Media Server (`:8096`)**, **Aria2 Next Downloader (`:6800`)**, **JDownloader 2 (`:9666`)**, **pyLoad (`:8001`)**, **qBittorrent (`:8080`)**, **Beszel Monitoring Hub (`:8090`) & Agent (`:45876`)**, **TapMap (`:8050`)**, and **GIZI App (`:8000`)**.

*Rule*: All new applications must be assigned to their corresponding tier, numbered with `# X. Launch <Name>`, and must NOT displace Tier 0 (Gateway) or Tier 1 (Core APIs) to the end of the script.

## Service Process Lifecycle & Execution Policy
- **Never start services as direct attached processes/daemons from Antigravity**: When Antigravity closes, reloads, or restarts, attached child processes and subshell jobs are terminated by the environment.
- **Always use dedicated startup scripts**: Launch persistent services using their designated startup script in the application working folder (e.g. `wscript.exe <app>-start.vbs` or `powershell.exe -File <app>-start.ps1`) or via `master-boot-launcher.ps1` so they execute completely detached under the Windows subsystem.
- **Post-Job Background Task Sweep**: After each job or task is finished, always check running background tasks/jobs for any lingering processes that are no longer needed and terminate them gracefully.

## Admin Dashboard Section Ordering (`www/admin.html`)
- **Log Rotation & Maintenance Section**: MUST ALWAYS remain in the very last place on the admin dashboard (`#dashboard-section`). If additional sections or management panels are added in the future, insert them above the Log Rotation & Maintenance section, never after it.

## WMI-Launched Services & Process Management

All persistent services in this workspace (e.g. `update-service.py`, `caddy.exe`) are started via **WMI `Win32_Process.Create`**, either directly or through a `.vbs` launcher that calls it. This makes the process **fully detached** — it has no meaningful parent PID (shows as `System`/PID 4 in Task Manager) and is immune to parent-shell teardown.

### Why `Get-Process`, `taskkill`, and `Stop-Process -Name` fail

| Method | Why it fails |
|--------|-------------|
| `Get-Process -Name pythonw` | Returns all `pythonw` instances — can't distinguish the right one without CommandLine |
| `Stop-Process -Name pythonw -Force` | Kills **all** pythonw processes indiscriminately |
| `taskkill /IM pythonw.exe` | Same — kills every instance |
| `Get-Process \| Where Name -eq ...` | No CommandLine access; can't match by script path |
| Port-based `netstat` → `taskkill /PID` | Works, but is brittle if port changes |

### Canonical Stop Pattern

Always stop services by matching on **CommandLine** via `Win32_Process` (CIM):

```powershell
# Stop by script name pattern (PowerShell) - MUST filter for python to avoid powershell self-kill
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -like '*python*' -and $_.CommandLine -like '*update-service.py*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Or via the dedicated stop script (preferred — use `/silent` to suppress blocking MsgBox):

```powershell
wscript.exe "C:\PortableApps\caddy\update-monitor-stop.vbs" /silent
```

**Never** attempt `Stop-Process -Name` or `taskkill /IM` for these services.

### Canonical Start Pattern

Always start via the designated `.vbs` launcher, which internally uses WMI:

```powershell
wscript.exe "C:\PortableApps\caddy\update-monitor-start.vbs"
```

The launcher includes a **port-busy guard** — it silently exits if the service is already running on its port, so it is safe to call idempotently.

#### Console Subsystem Binaries & Window Suppression (`jellyfin-start.vbs`)
Windows executables built as Console Subsystem (`IMAGE_SUBSYSTEM_WINDOWS_CUI`, such as `jellyfin.exe`) behave differently under WMI:
- WMI `Win32_Process.Create` with `ShowWindow = 0` does NOT pass `CREATE_NO_WINDOW` or honor `STARTF_USESHOWWINDOW` for console applications when invoked in an interactive session, causing Windows to allocate a visible cmd/console window (`conhost.exe`) on the desktop.
- For `jellyfin.exe`, [`jellyfin-start.vbs`](file:///C:/PortableApps/jellyfin/jellyfin-start.vbs) uses Windows Script Host's native `WshShell.Run(Cmd, 0, False)` (`SW_HIDE`). Because `wscript.exe` is a GUI subsystem binary, calling `WshShell.Run` with style `0` passes `STARTF_USESHOWWINDOW` with `wShowWindow = SW_HIDE` via Win32 `CreateProcess`, completely suppressing any cmd prompt window.
- Combined with a PowerShell port-busy guard (`-WindowStyle Hidden`), the launcher provides silent, idempotent background execution without exposing any console windows.

### Restart Sequence

```powershell
# 1. Stop silently
wscript.exe "C:\PortableApps\caddy\<app>-stop.vbs" /silent
Start-Sleep 2   # allow OS to release port binding
# 2. Start (idempotent — guard inside VBS prevents double-launch)
wscript.exe "C:\PortableApps\caddy\<app>-start.vbs"
# 3. Verify (allow ~10s for initial WinGet/service scan)
Start-Sleep 10
Get-NetTCPConnection -LocalPort <port> -ErrorAction SilentlyContinue
```

### Checking if a WMI-launched service is running

```powershell
# By port
Get-NetTCPConnection -LocalPort 8084 -ErrorAction SilentlyContinue

# By script name
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like '*update-service.py*' } |
  Select-Object ProcessId, CommandLine
```

### Service → Port → Script Map

| Service | Port | Start Script | Stop Script |
|---------|------|-------------|-------------|
| Caddy Reverse Proxy | 80 / 443 | `caddy-start.vbs` | `caddy-stop.vbs` |
| Admin Service Backend | 8085 | `admin-service/start-admin-service.vbs` | `admin-service/stop-admin-service.vbs /silent` |
| System Update Monitor | 8084 | `update-monitor-start.vbs` | `update-monitor-stop.vbs /silent` |
| Calibre Content Server | 8081 | `Calibre Portable/calibre-start.vbs` | `Calibre Portable/calibre-stop.vbs /silent` |
| Calibre-Web | 8083 | `Calibre-Web/calibre-web-start.vbs` | `Calibre-Web/calibre-web-stop.vbs /silent` |
| FileBrowser Quantum | 8082 (shared) | `FileBrowserQ/filebrowserq-start.vbs` | `FileBrowserQ/filebrowserq-stop.vbs /silent` |
| FileBrowser (Legacy) | 8082 (shared) | `filebrowser/filebrowser-start.vbs` | `filebrowser/filebrowser-stop.vbs /silent` |
| Aria2 Next Downloader | 6800 | `aria2-next/aria2-start.vbs` | `aria2-next/aria2-stop.vbs /silent` |
| TapMap | 8050 | `TapMap/tapmap-start.vbs` | `TapMap/tapmap-stop.vbs /silent` |
| pyLoad Download Manager | 8001 | `pyload/pyload-start.vbs` | `pyload/pyload-stop.vbs /silent` |
| GIZI App (SPPG Melong) | 8000 | `gizi/gizi-start.vbs` | `gizi/gizi-stop.vbs /silent` |
| Jellyfin Media Server | 8096 | `jellyfin/jellyfin-start.vbs` | `jellyfin/jellyfin-stop.vbs /silent` |
| qBittorrent | 8080 | `qBittorrentPortable/qbittorrent-start.vbs` | `qBittorrentPortable/qbittorrent-stop.vbs /silent` |
| Beszel Monitoring Hub | 8090 | `beszel/beszel-hub-start.vbs` | `beszel/beszel-hub-stop.vbs /silent` |
| Beszel Monitoring Agent | 45876 | `beszel/beszel-agent-start.vbs` | `beszel/beszel-agent-stop.vbs /silent` |
| 7-Zip Archiver | CLI (None) | *On-demand execution* | `7zip-update.ps1` (updater) |
| UnRAR Extraction Tool | CLI (None) | *On-demand execution* | `unrar-update.ps1` (updater) |

*Note on Port 8082 Sharing*: FileBrowser Quantum and legacy FileBrowser share port 8082 (`/files`). The Admin Dashboard backend automatically enforces mutual exclusion by stopping the running engine before starting the other.
*Note on CLI Utilities*: Standalone command-line archivers (7-Zip, UnRAR) do not bind to TCP ports or run persistent background daemons; they execute on-demand and are managed via dedicated in-place update engines with status `Ready` on the Admin Dashboard.
*Note on Calibre Library Auto-Sync*: The Admin Service Backend (`:8085`) runs a persistent background daemon thread (`calibre-library-monitor`) that tracks `metadata.db` across all Calibre libraries. When external writes from Calibre-Web (`:8083`) occur, it debounces for 5 seconds and automatically reloads Calibre Content Server (`:8081`) via `calibre-stop.vbs` and `calibre-start.vbs` to keep in-memory caches synchronized.


### On-Demand Elevated WinGet Updater Task (`StargazerWinGetElevatedUpdater`)

Machine-scope WinGet packages install to `%ProgramFiles%` and `HKLM`, requiring Administrator privileges. To allow the un-elevated `update-service.py` to trigger these upgrades on demand without blocking or prompting:

- **Scheduled Task Name**: `StargazerWinGetElevatedUpdater` (Runs as user `nukie` with `RunLevel: Highest`).
- **One-Time Registration**: Run `C:\PortableApps\caddy\register-elevated-updater.bat` (double-click in Explorer to trigger standard UAC prompt).
- **Unregistration**: Run `C:\PortableApps\caddy\unregister-elevated-updater.bat`.
- **IPC Protocol**: `update-service.py` writes `{id, action: "upgrade", status: "pending"}` to `C:\PortableApps\caddy\pending-winget-upgrade.json`, calls `schtasks /run /tn StargazerWinGetElevatedUpdater`, and polls for `status: "completed"`.
- **Execution Script**: `C:\PortableApps\caddy\winget-elevated-runner.ps1` executes `winget.exe upgrade --exact --id <id>`, appends output to `winget-upgrade.log`, and atomically updates the JSON file.
- **Graceful Fallback**: If the task is not registered, `update-service.py` (`is_elevated_task_available() == False`) seamlessly falls back to standard `run_winget` without failing.
- **Elevated Restart Sentinel Flags**: To allow non-elevated scripts and update engines to cleanly stop services running under Session 0 / `SYSTEM` (NSSM), scripts drop a flag file and trigger `schtasks /run /tn StargazerWinGetElevatedUpdater`. The elevated runner (`winget-elevated-runner.ps1`) terminates the process, clears the flag, and exits. Supported flags:
  - `caddy\update-service.flag` &mdash; System Update Monitor (Port 8084)
  - `caddy\admin-service\restart.flag` &mdash; Admin Service Backend (Port 8085)
  - `Calibre Portable\calibre.flag` &mdash; Calibre Content Server (`calibre-server.exe`, Port 8081)
  - `Calibre-Web\calibre-web.flag` &mdash; Calibre-Web (`calibreweb.exe`, Port 8083)
  - `jellyfin\jellyfin.flag` &mdash; Jellyfin Media Server (`jellyfin.exe`, Port 8096)
  - `qBittorrentPortable\qbittorrent.flag` &mdash; qBittorrent (`qbittorrent.exe`, Port 8080)
  - `aria2-next\aria2.flag` &mdash; Aria2 Next (`aria2c.exe`, Port 6800)
  - `FileBrowserQ\filebrowserq.flag` &mdash; FileBrowser Quantum (`filebrowserq.exe` / `filebrowser.exe`, Port 8082)
  - `beszel\beszel.flag` &mdash; Beszel Hub (`beszel.exe`, Port 8090)
  - `beszel\beszel-agent.flag` &mdash; Beszel Agent (`beszel-agent.exe`, Port 45876)
  - `TapMap\tapmap.flag` &mdash; TapMap (`tapmap.exe`, Port 8050)
  - `gizi\gizi.flag` &mdash; GIZI App (Port 8000)
  - `zed-remote-server\zed-remote-server.flag` &mdash; Zed Remote Server (`remote_server.exe`)

- **Stale Sentinel Flag Immunity & Boot Scrubbing**: If an abrupt host shutdown or reboot occurs before `StargazerWinGetElevatedUpdater` has a chance to clear an elevated sentinel flag, the stale `.flag` file could persist across reboots. Without mitigation, any subsequent scheduled or routine WinGet scan invoked by `update-service.py` would discover the leftover flag and terminate the newly booted service prematurely. To make services completely immune to this race condition:
  1. **Boot Pre-Flight Purge**: `master-boot-launcher.ps1` unconditionally sweeps and purges all sentinel `.flag` files across all application directories in Pre-Flight (Step 0) before initiating any service launches.
  2. **Service Launcher Self-Healing**: Individual launcher scripts (e.g. `tapmap-start.vbs`) actively check and remove their own `.flag` file (alongside any stale `.lock` files) before launching the binary.

### Universal 6-Step Updater Architecture (`*-update.ps1`) & `UpdateHelpers.psm1`

All custom update scripts in the workspace follow a unified 6-step acquisition, inspection, and lifecycle pattern, importing shared core logic from `C:\PortableApps\caddy\UpdateHelpers.psm1`:
1. **GitHub Auth Auto-Discovery (`Get-GitHubAuthHeaders`)**: Extracts GitHub Desktop tokens via `advapi32!CredReadW` from Windows Credential Manager to raise rate limits to 5,000 requests/hour.
2. **Pre-Update Backup Inspection & Cleanup (`Remove-SuperfluousBackups`)**: Once update eligibility is verified, scans application directories and `.update_cache` for previous, superseded, or lingering backup artifacts (`*.bak`, `*_backup*`, `backup/`) and purges them to prevent disk bloat before downloading or replacing files.
3. **Local Downloads Check (`Get-UserDownloadsFolders` + `Find-LocalUpdateBinary`)**: Resolves Downloads across registry, user profile, hardcoded `C:\Users\nukie\Downloads`, and all non-system profiles. Scans for existing matching installer/archive before hitting the network, copying into `.update_cache` without modifying the user's file.
4. **Multi-Stream Accelerated Download (`Find-Aria2Executable`)**: Locates `aria2c` in PATH or workspace `aria2-next` and executes 4-connection multi-stream download (`-s 4 -x 4 -k 1M`), gracefully falling back to `curl.exe` and `Invoke-WebRequest`.
5. **Session 0 Sentinel Stop Guard & Dual-Vector Detection**: When checking whether a service was running prior to stopping, updaters inspect both CIM process instances (including alternate binary names, e.g. `filebrowserq` vs `filebrowser`, `python` / `pythonw` with script matching) AND active TCP listening port connections (`Get-NetTCPConnection`). This ensures services stuck in initialization or running across session boundaries are reliably detected and preserved in `was_running.flag`. After calling local stop scripts, queries CIM for surviving processes and fires the elevated sentinel stop pattern if needed to cleanly handle NSSM/SYSTEM services. A `Start-Sleep -Seconds 2` cooldown follows to let the OS fully release kernel file handles before the swap. All backups are safely staged into `.update_cache\backup` with atomic rollback protection and post-update cleanup when `-KeepArtifacts` is omitted.
6. **File-Lock Retry Loop & Restart Resilience**: Binary/directory replacement is wrapped in a 5-attempt `for` loop (1-second sleep between attempts) so transient Windows file-lock delays after process stop do not abort the update. A `was_running.flag` sentinel is written to `.update_cache` before the service is stopped, and the restart gate checks `$wasRunning -or (Test-Path $wasRunningFlag) -or $Force.IsPresent` — guaranteeing the service is restarted even if a prior failed attempt already stopped it and a retry finds no running process. The flag is removed on successful restart.
7. **Post-Update Translation Pruning Hook**: If the service directory contains a `remove-unused-translations.ps1` script (e.g., Calibre, Calibre-Web, qBittorrent, JDownloader 2), the updater automatically executes it immediately after unpacking or file replacement before service restart. This keeps disk footprint lean by removing superfluous localization bundles and unneeded languages.
8. **Resilient 30-Second Health Probe Window**: After restarting services via their detached `.vbs` launcher, the updater polls the health endpoint in a 30-second loop (up to 30 attempts, 1s interval) using `Invoke-WebRequest -Proxy "" ...`. The explicit `-Proxy ""` parameter bypasses any system/WinINet proxy configurations for `127.0.0.1`/`localhost`, and the extended 30s window accommodates heavy bootstrapping, JVM spin-up, and PyInstaller decompression (e.g. Calibre-Web, Jellyfin).
9. **Caddy Build Server Version Override & Pre-Flight Binary Verification**: The upstream Caddy build API (`caddyserver.com/api/download`) ignores query parameter `version=<tag>` and compiles against its server baseline unless Caddy core is explicitly passed as a plugin package override: `p=github.com/caddyserver/caddy/v2@<tag>`. `caddy-update.ps1` passes this parameter, verifies the staged binary version (`stagedExe version`) against the target release before stopping the gateway, and `admin.js` extends gateway reconnect polling to 45 seconds to accommodate the restart and TLS binding cycle.


### Reentrant Lock Synchronization & Multi-Threaded Daemon Guidelines (Python Services)

In multi-threaded Python backend services (such as `caddy/admin-service/main.py` and `caddy/update-service.py`) running persistent background loops (e.g. `online_version_checker_loop`, `calibre_library_monitor`):
- **Reentrant Locks (`threading.RLock`)**: When a thread executing inside a synchronized lock context invokes another function or helper that also requires the same lock, a standard `threading.Lock()` triggers a permanent self-deadlock. Always use `threading.RLock()` for thread synchronization whenever reentrant call hierarchies exist (e.g. `check_single_service_online_version()` calling `save_online_versions_to_disk()`, or in-memory cache mutation helpers on `CACHE`).
- **Decoupled Disk Persistence**: When saving in-memory caches or version maps to disk, make a shallow or deep copy of the dictionary while holding the lock, release the lock immediately, and perform the disk file write outside the synchronized lock block. This prevents file system I/O latency from blocking concurrent API requests (such as `GET /admin-api/status`).

### System Update Monitor (:8084) Optimistic In-Memory Cache & Single-Click Pinning

In `caddy/update-service.py`, package pinning/unpinning operations (`action=pin`, `action=unpin`, `action=reset_pins`):
- **Never trigger asynchronous background re-scans before responding with HTTP 302**: Spawning a background thread (`refresh_all_caches()`) and immediately sending a redirect creates a race condition where the browser reloads within 10ms and reads stale in-memory cache data before the 1–4s multi-engine scan completes, forcing users into a confusing "second click".
- **Optimistic In-Memory Mutation**: Synchronously move packages between `CACHE["upgrades"]` and `CACHE["pins"]` under `threading.RLock()` (`apply_pin_to_cache`, `apply_unpin_to_cache`, `apply_reset_pins_to_cache`), recalculate summary counts via `_recalc_cache_counts_locked()`, and re-parse local `winget-cache.json` (`sync_winget_cache_to_memory()`) in < 2ms before sending the 302 redirect.
- **Deep-Link Tab Anchor Preservation**: Always preserve the caller's active tab by passing `&tab=pins` on unpin links and redirecting to `/updates#pins` instead of jumping away to `#winget`.
- **Available Version Metadata Retention**: Retain `available` version metadata across all pin cycles (`scan_winget`, `scan_npm`, `scan_pip`) so unpinned items immediately restore to the upgrades table with functional update buttons.

### Session 0 (LocalSystem) Environment Redirection for CLI Tools

When persistent services boot via `StargazerMediaServices` (NSSM) under `NT AUTHORITY\SYSTEM`, user environment variables (`%USERPROFILE%`, `%APPDATA%`, `%LOCALAPPDATA%`) point to `C:\Windows\System32\config\systemprofile`. This causes CLI tools (`winget`, `npm`, `uv`) to fail with file not found or `EPERM` errors.

To guarantee seamless operation across both user sessions and Session 0:
- All CLI tool runners (`run_winget`, `run_npm`, `run_uv`) pass `get_service_env()`, which dynamically redirects `USERPROFILE`, `APPDATA`, and `LOCALAPPDATA` to `C:\Users\nukie` when running under `systemprofile`, and prepends user tool paths to `PATH`.
- Global NPM operations inject `--prefix C:\Users\nukie\AppData\Roaming\npm` to prevent Arborist engine permissions collisions in `systemprofile`.
- `scan_npm()` defensively checks for and discards top-level `error` responses from `npm outdated --json` so error payloads are logged instead of appearing as ghost package rows.

### Stargazer Media Services NSSM Windows Service (`StargazerMediaServices`)

Stargazer Media Services uses **NSSM (Non-Sucking Service Manager)** (`C:\PortableApps\NSSM\nssm.exe`) to run the boot orchestrator at system boot in Windows Session 0 under `LocalSystem` (`NT AUTHORITY\SYSTEM`).

- **Service Name**: `StargazerMediaServices`
- **Display Name**: `Stargazer Media Services`
- **Runner Script**: `C:\PortableApps\stargazer-service.ps1` (invokes `master-boot-launcher.ps1` and monitors service lifecycle)
- **Shutdown Orchestrator**: `C:\PortableApps\master-stop.ps1` (gracefully stops all tiers in reverse order)
- **Log Files**: `C:\PortableApps\caddy\logs\nssm-stargazer.log` and `caddy\logs\master-boot.log`
- **Registration**: Run `C:\PortableApps\register-service-nssm.bat` (self-elevating UAC launcher). Automatically unregisters legacy `StargazerMediaServicesBoot` task.
- **Unregistration**: Run `C:\PortableApps\unregister-service-nssm.bat` (self-elevating UAC launcher).
- **Control Commands**:
  ```powershell
  Start-Service -Name StargazerMediaServices
  Stop-Service -Name StargazerMediaServices
  Restart-Service -Name StargazerMediaServices
  ```
- **Why NSSM**: Eliminates user `S4U` boot-time logon tokens, permanently preventing Windows DPAPI master key locking and user credential loss across reboots.

## Modern Web Standards & Frontend Architecture Guidelines (`/modern-web-guidance`)

When modifying, maintaining, or creating first-party web interfaces in this workspace (e.g. `caddy/www`, `admin.html`, `calc.html`):

1. **Strict Zero-Inline CSP Architecture**:
   - Zero inline `<style>` blocks (all styles externalized to `/css/<name>.css`).
   - Zero inline `<script>` blocks (all scripts externalized to `/js/<name>.js`).
   - Zero inline `on*` event handlers (use `addEventListener` or DOM data delegation `data-action="..."`).
2. **Native HTML5 Overlays (`<dialog>` & `::backdrop`)**:
   - Always use native `<dialog>` elements with `.showModal()` and `.close()` for modals and overlays.
   - Do NOT use custom backdrop divs with manual `z-index` and class toggles. Native `<dialog>` provides automatic focus trapping, top-layer stacking, background `inert` handling, and native `Escape` key dismissal.
   - Style backdrops via `dialog::backdrop` (e.g. `backdrop-filter: blur(8px)`).
3. **Core Web Vitals & Cumulative Layout Shift (CLS)**:
   - Always specify explicit `width` and `height` attributes on `<img>` tags.
   - Use `decoding="async"` for non-critical images to keep parsing off the main thread.
4. **Theme & Native UA Controls**:
   - Declare static `color-scheme: dark;` on `html[data-theme="dark"]` and `color-scheme: light;` on `html[data-theme="light"]` in CSS.
   - This ensures native browser form inputs, select dropdowns, datetime pickers, and scrollbars adapt instantly to the active theme without waiting for JavaScript execution.
   - Standardize scrollbars using standard Baseline properties (`scrollbar-width: thin; scrollbar-color: ...`).
5. **Typographic Polish**:
   - Apply `text-wrap: balance;` to headers, card titles, and modal titles (`h1`, `h2`, `.card-title`, `.modal-title`).
   - Apply `text-wrap: pretty;` to multi-line descriptions and body copy to prevent dangling single words (orphans/widows).
6. **Interaction-Gated Form Validation**:
   - Use `:user-valid` and `:user-invalid` pseudo-classes rather than `:valid` / `:invalid` to prevent premature red error outlines on untouched form fields.
7. **Accessible Motion Reduction**:
   - Always include `@media (prefers-reduced-motion: reduce)` rules to dampen transforms (`translateY`, scale) and heavy animations for users with vestibular sensitivity.

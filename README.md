# DroidForge

**Android pentest environment manager** — install, sync, diagnose, and repair your entire mobile security toolkit from one CLI.

DroidForge is evolving from a tool manager into a full **Android penetration environment**: one command to get adb, frida, jadx, apktool, and the rest of your kit installed, version-locked, and working together. It solves dependency hell — tools like `objection`, `r2frida`, and `frida-tools` all require the exact same `frida` version, and `apktool` needs a compatible JDK.

## Install

```bash
git clone <repo-url> droidforge
cd droidforge
pip install -e ".[dev]"
```

Run via the installed entrypoint or as a module:

```bash
droidforge --help          # full ASCII banner + commands
droidforge status          # compact banner + tool table
python -m droidforge doctor
```

Set `DROIDFORGE_NO_BANNER=1` or pass `--no-banner` to suppress the ASCII art (useful for scripts/CI).

## Use it as a self-contained pentest environment (recommended)

Turn any repo into a portable Android pentest kit. Tools are downloaded into
`./.droidforge/tools/`, version-locked, and added to your `PATH` on demand —
the heavy binaries stay **gitignored**, while the config and lockfile are
committed for reproducibility.

```bash
cd my-engagement-repo

droidforge init                 # create droidforge.toml + .gitignore + .droidforge/tools
droidforge up                   # install the profile + set up frida (one command)
droidforge console              # interactive pentest REPL (recommended)
droidforge shell                # …or a raw subshell with every tool on PATH
```

Inside `droidforge shell`, tools like `jadx`, `apktool`, `objection`, and
`frida` are directly on your `PATH`. Type `exit` to leave.

## Pentest a rooted emulator — full walkthrough

Assuming a rooted emulator/device is running with USB debugging (e.g. a
Genymotion / rooted AVD / Corellium instance, visible via `adb devices`):

```bash
# 0) one-time: build the dynamic-analysis kit (adb, frida, objection, …)
droidforge up --profile dynamic

# 1) drop into the interactive console
droidforge console
```

Then drive the engagement from the **DroidForge console**:

```text
droidforge [no-device | no-target]> devices          # auto-selects a single device
droidforge [emulator-5554 | no-target]> ready        # push + start frida-server
droidforge [emulator-5554 | no-target]> apps owasp   # find your target (filter)
droidforge [emulator-5554 | no-target]> target com.example.app
droidforge [emulator-5554 | com.example.app]> status # device + frida + target summary
droidforge [emulator-5554 | com.example.app]> proxy 10.0.2.2:8080   # route HTTPS to Burp
droidforge [emulator-5554 | com.example.app]> hook   # SSL pinning + root bypass (spawn)
droidforge [emulator-5554 | com.example.app]> objection             # interactive explorer
droidforge [emulator-5554 | com.example.app]> logcat com.example.app   # watch logs
droidforge [emulator-5554 | com.example.app]> exit
```

The console keeps **live session state** (selected device + target app), so you
don't retype serials/packages. Every verb maps to the same engines the flat
CLI uses (`device ready`, `bypass`, `objection`, …) — just faster to chain.

### Console commands

| Verb | Description |
|------|-------------|
| `devices` / `use <serial>` | List devices / select the active one |
| `apps [filter]` | List installed apps (running ones marked) |
| `target <package>` | Set the app under test (accepts substrings) |
| `status` | Device + frida runtime + frida-server + target |
| `ready` | Push & start frida-server matching local frida |
| `hook` / `bypass [ssl\|root\|all]` | Run SSL/root bypass on the target |
| `objection [args]` | Open Objection's explorer on the target |
| `proxy <host:port>` / `proxy off` | Set/clear the device global HTTP proxy |
| `logcat [filter]` | Stream device logs |
| `screenshot [file.png]` | Capture the screen to a local PNG |
| `adb <args>` / `adbshell` | Run adb / open an interactive adb shell |
| `pull` / `push` | Copy files off/onto the device |
| `ps` / `run <tool> [args]` | List processes / run any DroidForge tool |
| `clear` · `help` · `exit` | Housekeeping |

Reproduce the exact kit on another machine:

```bash
droidforge lock                 # write droidforge.lock.toml (commit this)
# … teammate clones the repo …
droidforge restore              # install the locked tools + frida runtime
```

## Quick Start

```bash
# One-command environment (auto-inits a repo-local workspace inside a git repo)
droidforge up --profile dynamic

# See / inspect profiles
droidforge profile list
droidforge profile show static

# Drive an engagement interactively
droidforge console              # pentest REPL with live device + target state

# Put every installed tool on PATH
droidforge shell                # subshell (easiest)
droidforge env                  # or print the PATH snippet for your shell

# Get a single tool, downloaded + on PATH + verified
droidforge get jadx

# Get a device frida-ready in one shot (runtime + push-server + verify)
droidforge device ready

# Check what's installed vs latest (use --offline to skip network)
droidforge status --offline

# Diagnose / auto-repair
droidforge doctor
droidforge fix --bootstrap
```

## Commands

### Get started

| Command | Description |
|---------|-------------|
| `droidforge init [--profile NAME] [--force]` | Create a repo-local workspace (config + `.gitignore` + `.droidforge/tools`) |
| `droidforge up [--profile NAME] [--no-frida] [--yes]` | Build the environment: install a profile + set up frida + write lockfile |
| `droidforge console [--device SERIAL]` | Interactive pentest REPL with live device + target state |
| `droidforge shell` | Open a subshell with every installed tool on `PATH` |
| `droidforge profile list` / `show <name>` | List profiles or inspect a profile's tools |
| `droidforge lock` | Write `droidforge.lock.toml` from the current kit |
| `droidforge restore [--yes]` | Install tools/frida exactly as recorded in the lockfile |

### Environment

| Command | Description |
|---------|-------------|
| `droidforge status [--category NAME] [--offline]` | Table of installed vs latest versions |
| `droidforge install <tool> [--version X.Y.Z] [--force]` | Install tool + dependencies |
| `droidforge get <tool>` | Install a tool, put it on `PATH`, and verify it's runnable |
| `droidforge install --all` | Install entire registry (topological order) |
| `droidforge update [tool] [--all] [--force]` | Update to latest; pin groups update atomically |
| `droidforge pin <tool> <version>` | Lock tool/pin-group version in config |
| `droidforge unpin <tool>` | Remove version lock |
| `droidforge env [--frida-only]` | Print PATH setup for all tools (or just the frida venv) |
| `droidforge doctor` | Environment health report |
| `droidforge fix [--dry-run] [--yes] [--bootstrap] [--aggressive]` | Diagnose and auto-repair issues |

### Device & arsenal

| Command | Description |
|---------|-------------|
| `droidforge device list` | List connected ADB devices |
| `droidforge device ready [--device SERIAL]` | Ensure frida runtime + push frida-server + verify with `frida-ps -U` |
| `droidforge push-server [--device SERIAL] [--no-start]` | Push frida-server matching local frida |
| `droidforge info [tool]` | Tool catalog, or detail card for one tool |
| `droidforge arsenal` | List runnable tool CLIs (ready / missing) |
| `droidforge run <tool> [args…]` | Run a tool via explicit dispatch |
| `droidforge <tool> [args…]` | Direct dispatch (e.g. `droidforge frida -U`) |
| `droidforge config` | Show `droidforge.toml` |
| `droidforge config set <key> <value>` | Update a setting |

## Profiles

Profiles are curated tool bundles for one-command setup with `droidforge up --profile NAME`:

| Profile | Tools |
|---------|-------|
| `minimal` | adb, frida, frida-tools |
| `dynamic` | frida stack, objection, r2frida, medusa |
| `static` | jadx, apktool, smali/baksmali, dex2jar, enjarify |
| `traffic` | mitmproxy, apk-mitm |
| `scanners` | MobSF, nuclei, drozer |
| `full` | everything auto-installable in the registry |

## Repo-local layout

`droidforge init` produces a portable, reproducible workspace:

```text
my-repo/
├── droidforge.toml         # committed — settings + profile + pins
├── droidforge.lock.toml    # committed — exact installed versions (droidforge lock)
├── .gitignore              # auto-updated to ignore downloaded tools
└── .droidforge/
    ├── tools/              # downloaded CLIs/jars (gitignored)
    └── cache/              # PyPI/GitHub cache (gitignored)
```

Frida runtimes live in per-version venvs under `~/.droidforge/venvs/` (machine-specific,
recreated by `droidforge use` / `droidforge restore`), so they're never committed.

## Configuration

`~/.droidforge/droidforge.toml` (or `./droidforge.toml` in the project directory):

```toml
[settings]
adb_path = "adb"
java_path = "java"
install_dir = "~/.droidforge/tools"
auto_push_frida_server = false

[pins]
frida = "16.1.4"   # pins the entire frida group

[ignored]
tools = ["ghidra", "wireshark"]
```

### Frida pin group (important)

The **frida runtime** (pip package `frida`) uses the version you care about for device hooks — e.g. `17.11.0`.

**frida-tools** and **objection** have **their own** pip version numbers (e.g. `14.9.0`, `1.12.5`) but must be compatible with the frida runtime. DroidForge never installs `frida-tools==17.11.0` — that was the old bug.

| Command | What it does |
|---------|----------------|
| `droidforge use 17.11.0` | **nvm-style** — create/select isolated venv for this runtime |
| `droidforge use latest` | Use latest frida release |
| `droidforge sync frida` | Align global pip: exact frida + upgrade companions |
| `droidforge pin frida 17.11.0` | Save preference in config (then `use` or `sync`) |
| `droidforge versions frida` | Show active, pinned, installed, PyPI releases |
| `droidforge env` | Print `PATH` snippet for active venv |

After `droidforge use X`, run the `droidforge env` output in your shell, then `droidforge push-server`.

### Arsenal — run tools through DroidForge

Tools with a CLI are registered as native commands:

```bash
droidforge arsenal              # ready vs missing
droidforge frida --version
droidforge frida-ps -U
droidforge objection explore
droidforge jadx --help
droidforge run mitmproxy        # explicit form
```

Resolution order: **active frida venv** → `~/.droidforge/tools/*/bin` → system `PATH`.

## Tool Categories

- **Dynamic Analysis** — frida, objection, r2frida, medusa
- **Static Analysis** — jadx, apktool, smali, radare2, ghidra (manual)
- **Traffic Interception** — mitmproxy, apk-mitm, Burp (manual)
- **Device & ADB** — adb, scrcpy, pidcat, androguard
- **APK Manipulation** — uber-apk-signer, apksigner (manual)
- **Automated Scanners** — MobSF, drozer, nuclei
- **Data & Storage** — binwalk, trufflehog, gitleaks
- **Network** — nmap, tcpdump, wireshark (manual)

Manual-only tools appear in `status` and `doctor` with install instructions but are not auto-installed.

## `droidforge fix`

Three-phase repair flow: **diagnose → plan → apply → re-check**.

**Safe by default** (from `doctor` findings):

| Issue | Action |
|-------|--------|
| Frida pin group mismatch | Sync or reinstall entire group (respects `[pins]`) |
| frida-server not running | `push-server` |
| adb missing | Install platform-tools |
| Broken pip/github install | Reinstall tool |

**Flags:**

| Flag | Effect |
|------|--------|
| `--dry-run` | Show plan only |
| `--yes` / `-y` | Skip confirmation |
| `--bootstrap` | Install missing core env tools: adb, frida, jadx, apktool, mitmproxy, … |
| `--aggressive` | Also update all outdated registry tools |
| `--only frida,server` | Limit to categories |

Manual steps (Python upgrade, Java, Node.js, no device connected) are listed but never auto-applied.

### Impact levels

Each fix shows an **Impact** column — how disruptive the change is, **not** a security rating.

| Level | Meaning |
|-------|---------|
| **Low impact** | One tool or device; easily reversed (install adb, push frida-server, reinstall one tool) |
| **Medium impact** | Multiple packages or version bumps together (sync frida pin group, `--aggressive` updates) |
| **High impact / manual** | DroidForge cannot apply automatically (upgrade Python, install JDK, plug in a device) |

Every `droidforge fix` run prints a legend panel explaining these before the plan. Use `--no-legend` to hide it.

## Roadmap: Pentest Environment

DroidForge aims to become a batteries-included Android pentest environment:

- **Today** — tool registry, version pinning, doctor, fix, frida-server push
- **Next** — environment profiles (`minimal`, `dynamic`, `full`), PATH/setup shell hook, workspace templates
- **Future** — bundled configs (mitmproxy certs, MobSF docker compose), project scaffolds, CI-ready headless mode

## GitHub API

Release versions are fetched from the GitHub Releases API with a 1-hour cache in `~/.droidforge/cache/`. Set `GITHUB_TOKEN` to avoid rate limits.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT

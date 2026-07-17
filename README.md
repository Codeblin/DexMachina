# PinDroid

[![CI](https://github.com/Codeblin/pindroid/actions/workflows/ci.yml/badge.svg)](https://github.com/Codeblin/pindroid/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![Security policy](https://img.shields.io/badge/security-policy-green)](SECURITY.md)

**Android pentest environment manager** — install, sync, diagnose, and repair your entire mobile security toolkit from one CLI.

PinDroid is evolving from a tool manager into a full **Android penetration environment**: one command to get adb, frida, jadx, apktool, and the rest of your kit installed, version-locked, and working together. It solves dependency hell — tools like `objection`, `r2frida`, and `frida-tools` all require the exact same `frida` version, and `apktool` needs a compatible JDK.

## Why PinDroid

Most Android pentest setups grow from shell history, old notes, and a handful of one-off install scripts. PinDroid turns that into a repo-local, reproducible environment: curated profiles, version pins, a lockfile, Frida runtime isolation, device readiness checks, and `doctor`/`fix` when the setup drifts.

It is not a replacement for MobSF, Corellium, Burp, or manual reverse-engineering judgment. It is the glue layer that gets a consistent workstation and rooted emulator/device ready faster than rebuilding the same adb/frida/objection/jadx setup for every engagement.

## Trust and Support

- Trust model: [THREAT_MODEL.md](THREAT_MODEL.md)
- Vulnerability reporting: [SECURITY.md](SECURITY.md)
- Contributing and adding tools: [CONTRIBUTING.md](CONTRIBUTING.md)
- Release process: [docs/RELEASE.md](docs/RELEASE.md)
- Branch protection checklist: [.github/BRANCH_PROTECTION.md](.github/BRANCH_PROTECTION.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

### Support matrix

| Host | Status | Notes |
| --- | --- | --- |
| Ubuntu/Debian Linux | Supported in CI | Primary development target; `apt` helpers expect Debian-style systems. |
| macOS Intel/Apple Silicon | Supported in CI | Homebrew-backed tools require `brew`. |
| Windows native | Unit-tested in CI | Core CLI paths are tested; some upstream tools have limited Windows support. |
| WSL2 | Not officially supported yet | Often works for host-only commands, but USB/emulator workflows need manual validation. |

### Known good device setups

| Setup | Status |
| --- | --- |
| Stock AVD | CI smoke-tested for adb/emulator basics |
| Rooted AVD | CI integration job boots an AVD and runs `device ready` + `frida-ps -U` |
| Genymotion | Expected to work, needs published validation |
| Corellium | Expected to work, needs published validation |

## Install

### Recommended: pipx

`pipx` installs PinDroid in an isolated environment and exposes the
`pindroid` command on your shell `PATH`.

```bash
# Kali/Debian/Ubuntu
sudo apt update
sudo apt install -y pipx
pipx ensurepath
pipx install pindroid
```

On other Python installs where `pipx` is not packaged by the OS:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
python -m pipx install pindroid
```

Restart your terminal, then verify:

```bash
pindroid --help
```

### PyPI with pip

```bash
python -m pip install pindroid
```

On Kali, Debian 12+, Ubuntu 23.04+, and other PEP 668 distributions, system
Python may reject this with `externally-managed-environment`. Use `pipx`
instead, or install inside a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pindroid
pindroid --help
```

Avoid `--break-system-packages` unless you intentionally want to modify the OS
Python environment.

If the install succeeds but `pindroid` is not found, your Python scripts
directory is not on `PATH`. You can still run PinDroid as a module:

```bash
python -m pindroid --help
```

Or add the scripts directory printed by pip to your shell `PATH`. Common fixes:

```bash
# Linux/macOS user installs
python -m pip install --user pindroid
export PATH="$HOME/.local/bin:$PATH"

# Windows PowerShell user installs
py -m pip install --user pindroid
$env:PATH = "$env:APPDATA\Python\Python311\Scripts;$env:PATH"
```

On Windows, the exact `Python311` part depends on your Python version. If you
use the Python launcher, this always works even when the console script is not
on `PATH`:

```powershell
py -m pindroid --help
```

### From GitHub

Install the latest `master` directly:

```bash
python -m pip install "git+https://github.com/Codeblin/PinDroid.git"
```

Install a specific release tag:

```bash
python -m pip install "git+https://github.com/Codeblin/PinDroid.git@v0.1.0"
```

### Developer install

```bash
git clone https://github.com/Codeblin/pindroid.git
cd pindroid
python -m pip install -e ".[dev]"
```

Run via the installed entrypoint or as a module:

```bash
pindroid --help          # full ASCII banner + commands
pindroid status          # compact banner + tool table
python -m pindroid doctor
```

Set `PINDROID_NO_BANNER=1` or pass `--no-banner` to suppress the ASCII art (useful for scripts/CI).

## Use it as a self-contained pentest environment (recommended)

Turn any repo into a portable Android pentest kit. Tools are downloaded into
`./.pindroid/tools/`, version-locked, and added to your `PATH` on demand —
the heavy binaries stay **gitignored**, while the config and lockfile are
committed for reproducibility.

```bash
cd my-engagement-repo

pindroid init                 # create pindroid.toml + .gitignore + .pindroid/tools
pindroid up                   # install the profile + set up frida (one command)
pindroid console              # interactive pentest REPL (recommended)
pindroid shell                # …or a raw subshell with every tool on PATH
```

Inside `pindroid shell`, tools like `jadx`, `apktool`, `objection`, and
`frida` are directly on your `PATH`. Type `exit` to leave.

If `doctor` or `fix` reports that a managed tool is installed but not on your
shell `PATH`, use PinDroid's managed environment instead of editing global
shell startup files:

```bash
pindroid shell
# or:
eval "$(pindroid env)"
```

## Pentest a rooted emulator — full walkthrough

Assuming a rooted emulator/device is running with USB debugging (e.g. a
Genymotion / rooted AVD / Corellium instance, visible via `adb devices`):

```bash
# 0) one-time: build the dynamic-analysis kit (adb, frida, objection, …)
pindroid up --profile dynamic

# 1) drop into the interactive console
pindroid console
```

Then drive the engagement from the **PinDroid console**:

```text
pindroid [no-device | no-target]> devices          # auto-selects a single device
pindroid [emulator-5554 | no-target]> ready        # push + start frida-server
pindroid [emulator-5554 | no-target]> apps owasp   # find your target (filter)
pindroid [emulator-5554 | no-target]> target com.example.app
pindroid [emulator-5554 | com.example.app]> status # device + frida + target summary
pindroid [emulator-5554 | com.example.app]> proxy 10.0.2.2:8080   # route HTTPS to Burp
pindroid [emulator-5554 | com.example.app]> hook   # SSL pinning + root bypass (spawn)
pindroid [emulator-5554 | com.example.app]> objection             # interactive explorer
pindroid [emulator-5554 | com.example.app]> logcat com.example.app   # watch logs
pindroid [emulator-5554 | com.example.app]> exit
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
| `hook [--spawn]` / `bypass [ssl\|root\|all] [--spawn]` | Attach SSL/root bypass to a running target; optionally spawn |
| `objection [args]` | Open Objection's explorer on the target |
| `proxy <host:port>` / `proxy off` | Set/clear the device global HTTP proxy |
| `logcat [filter]` | Stream device logs |
| `screenshot [file.png]` | Capture the screen to a local PNG |
| `adb <args>` / `adbshell` | Run adb / open an interactive adb shell |
| `pull` / `push` | Copy files off/onto the device |
| `ps` / `run <tool> [args]` | List processes / run any PinDroid tool |
| `clear` · `help` · `exit` | Housekeeping |

Reproduce the exact kit on another machine:

```bash
pindroid lock                 # write pindroid.lock.toml (commit this)
# … teammate clones the repo …
pindroid restore              # install the locked tools + frida runtime
```

## Quick Start

```bash
# One-command environment (auto-inits a repo-local workspace inside a git repo)
pindroid up --profile dynamic

# See / inspect profiles
pindroid profile list
pindroid profile show static

# Drive an engagement interactively
pindroid console              # pentest REPL with live device + target state

# Put every installed tool on PATH
pindroid shell                # subshell (easiest)
pindroid env                  # or print the PATH snippet for your shell

# Get a single tool, downloaded + on PATH + verified
pindroid get jadx

# Get a device frida-ready in one shot (runtime + push-server + verify)
pindroid device ready

# Check what's installed vs latest (use --offline to skip network)
pindroid status --offline

# Diagnose / auto-repair
pindroid doctor
pindroid fix --bootstrap
```

### When to run `up`

Run `pindroid up` when creating an environment, after cloning an engagement
workspace, or after changing its profile, pins, or lockfile. It is safe to run
again: tools and Frida environments that already satisfy the configuration are
skipped. Use `pindroid update` for upgrades and `--force` only when you
intentionally want a reinstall.

For a normal daily pentest session, you usually only need:

```bash
pindroid device ready          # reconnect/restart the matching frida-server
pindroid console               # resume device + target workflow
```

## Commands

### Get started

| Command | Description |
|---------|-------------|
| `pindroid init [--profile NAME] [--force]` | Create a repo-local workspace (config + `.gitignore` + `.pindroid/tools`) |
| `pindroid up [--profile NAME] [--no-frida] [--yes]` | Build the environment: install a profile + set up frida + write lockfile |
| `pindroid console [--device SERIAL]` | Interactive pentest REPL with live device + target state |
| `pindroid shell` | Open a subshell with every installed tool on `PATH` |
| `pindroid profile list` / `show <name>` | List profiles or inspect a profile's tools |
| `pindroid lock` | Write `pindroid.lock.toml` from the current kit |
| `pindroid restore [--yes]` | Install tools/frida exactly as recorded in the lockfile |

### Environment

| Command | Description |
|---------|-------------|
| `pindroid status [--category NAME] [--offline]` | Table of installed vs latest versions |
| `pindroid install <tool> [--version X.Y.Z] [--force]` | Install tool + dependencies |
| `pindroid get <tool>` | Install a tool, put it on `PATH`, and verify it's runnable |
| `pindroid install --all` | Install entire registry (topological order) |
| `pindroid update [tool] [--all] [--force]` | Update to latest; pin groups update atomically |
| `pindroid pin <tool> <version>` | Lock tool/pin-group version in config |
| `pindroid unpin <tool>` | Remove version lock |
| `pindroid env [--frida-only]` | Print PATH setup for all tools (or just the frida venv) |
| `pindroid doctor` | Environment health report |
| `pindroid fix [--dry-run] [--yes] [--bootstrap] [--aggressive]` | Diagnose and auto-repair issues |

### Device & arsenal

| Command | Description |
|---------|-------------|
| `pindroid device list` | List connected ADB devices |
| `pindroid device ready [--device SERIAL]` | Ensure frida runtime + push frida-server + verify with `frida-ps -U` |
| `pindroid push-server [--device SERIAL] [--no-start]` | Push frida-server matching local frida |
| `pindroid info [tool]` | Tool catalog, or detail card for one tool |
| `pindroid arsenal` | List runnable tool CLIs (ready / missing) |
| `pindroid run <tool> [args…]` | Run a tool via explicit dispatch |
| `pindroid <tool> [args…]` | Direct dispatch (e.g. `pindroid frida -U`) |
| `pindroid config` | Show `pindroid.toml` |
| `pindroid config set <key> <value>` | Update a setting |

## Profiles

Profiles are curated tool bundles for one-command setup with `pindroid up --profile NAME`:

| Profile | Tools |
|---------|-------|
| `minimal` | adb, frida, frida-tools |
| `dynamic` | frida stack, objection, r2frida, medusa |
| `static` | jadx, apktool, smali/baksmali, dex2jar, enjarify |
| `traffic` | mitmproxy, apk-mitm |
| `scanners` | MobSF, nuclei, drozer |
| `full` | everything auto-installable in the registry |

## Repo-local layout

`pindroid init` produces a portable, reproducible workspace:

```text
my-repo/
├── pindroid.toml         # committed — settings + profile + pins
├── pindroid.lock.toml    # committed — exact installed versions (pindroid lock)
├── .gitignore              # auto-updated to ignore downloaded tools
└── .pindroid/
    ├── tools/              # downloaded CLIs/jars (gitignored)
    └── cache/              # PyPI/GitHub cache (gitignored)
```

Frida runtimes live in per-version venvs under `~/.pindroid/venvs/` (machine-specific,
recreated by `pindroid use` / `pindroid restore`), so they're never committed.

## Configuration

`~/.pindroid/pindroid.toml` (or `./pindroid.toml` in the project directory):

```toml
[settings]
adb_path = "adb"
java_path = "java"
install_dir = "~/.pindroid/tools"
auto_push_frida_server = false

[pins]
frida = "16.1.4"   # pins the entire frida group

[ignored]
tools = ["ghidra", "wireshark"]
```

### Frida pin group (important)

The **frida runtime** (pip package `frida`) uses the version you care about for device hooks — e.g. `17.11.0`.

**frida-tools** and **objection** have **their own** pip version numbers (e.g. `14.9.0`, `1.12.5`) but must be compatible with the frida runtime. PinDroid never installs `frida-tools==17.11.0` — that was the old bug.

| Command | What it does |
|---------|----------------|
| `pindroid use 17.11.0` | **nvm-style** — create/select isolated venv for this runtime |
| `pindroid use latest` | Use latest frida release |
| `pindroid sync frida` | Align global pip: exact frida + upgrade companions |
| `pindroid pin frida 17.11.0` | Save preference in config (then `use` or `sync`) |
| `pindroid versions frida` | Show active, pinned, installed, PyPI releases |
| `pindroid env` | Print `PATH` snippet for active venv |

After `pindroid use X`, run the `pindroid env` output in your shell, then `pindroid push-server`.

### Arsenal — run tools through PinDroid

Tools with a CLI are registered as native commands:

```bash
pindroid arsenal              # ready vs missing
pindroid frida --version
pindroid frida-ps -U
pindroid objection explore
pindroid jadx --help
pindroid run mitmproxy        # explicit form
```

Resolution order: **active frida venv** → `~/.pindroid/tools/*/bin` → system `PATH`.

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

## `pindroid fix`

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
| **High impact / manual** | PinDroid cannot apply automatically (upgrade Python, install JDK, plug in a device) |

Every `pindroid fix` run prints a legend panel explaining these before the plan. Use `--no-legend` to hide it.

## Roadmap: Pentest Environment

PinDroid aims to become a batteries-included Android pentest environment:

- **Today** — tool registry, version pinning, doctor, fix, frida-server push
- **Next** — environment profiles (`minimal`, `dynamic`, `full`), PATH/setup shell hook, workspace templates
- **Future** — bundled configs (mitmproxy certs, MobSF docker compose), project scaffolds, CI-ready headless mode

## GitHub API

Release versions are fetched from the GitHub Releases API with a 1-hour cache in `~/.pindroid/cache/`. Set `GITHUB_TOKEN` to avoid rate limits.

On Kali or shared networks you may hit unauthenticated GitHub API limits during
`pindroid up`, `install`, or `fix --bootstrap`. Create a fine-grained GitHub
token with read-only public repository access and export it before retrying:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
pindroid fix --bootstrap
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT

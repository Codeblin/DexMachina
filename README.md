# DexMachina

[![CI](https://github.com/Codeblin/dexmachina/actions/workflows/ci.yml/badge.svg)](https://github.com/Codeblin/dexmachina/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![Security policy](https://img.shields.io/badge/security-policy-green)](SECURITY.md)

**Android pentest environment manager** — install, sync, diagnose, and repair your entire mobile security toolkit from one CLI.

DexMachina is evolving from a tool manager into a full **Android penetration environment**: one command to get adb, frida, jadx, apktool, and the rest of your kit installed, version-locked, and working together. It solves dependency hell — tools like `objection`, `r2frida`, and `frida-tools` all require the exact same `frida` version, and `apktool` needs a compatible JDK.

## Why DexMachina

Most Android pentest setups grow from shell history, old notes, and a handful of one-off install scripts. DexMachina turns that into a repo-local, reproducible environment: curated profiles, version pins, a lockfile, Frida runtime isolation, device readiness checks, and `doctor`/`fix` when the setup drifts.

It is not a replacement for MobSF, Corellium, Burp, or manual reverse-engineering judgment. It is the glue layer that gets a consistent workstation and rooted emulator/device ready faster than rebuilding the same adb/frida/objection/jadx setup for every engagement.

## Trust and Support

- Trust model: [THREAT_MODEL.md](THREAT_MODEL.md)
- Vulnerability reporting: [SECURITY.md](SECURITY.md)
- Contributing and adding tools: [CONTRIBUTING.md](CONTRIBUTING.md)
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
| Rooted AVD | Planned Frida-ready integration coverage |
| Genymotion | Expected to work, needs published validation |
| Corellium | Expected to work, needs published validation |

## Install

```bash
git clone https://github.com/Codeblin/dexmachina.git
cd dexmachina
pip install -e ".[dev]"
```

Run via the installed entrypoint or as a module:

```bash
dexmachina --help          # full ASCII banner + commands
dexmachina status          # compact banner + tool table
python -m dexmachina doctor
```

Set `DEXMACHINA_NO_BANNER=1` or pass `--no-banner` to suppress the ASCII art (useful for scripts/CI).

## Use it as a self-contained pentest environment (recommended)

Turn any repo into a portable Android pentest kit. Tools are downloaded into
`./.dexmachina/tools/`, version-locked, and added to your `PATH` on demand —
the heavy binaries stay **gitignored**, while the config and lockfile are
committed for reproducibility.

```bash
cd my-engagement-repo

dexmachina init                 # create dexmachina.toml + .gitignore + .dexmachina/tools
dexmachina up                   # install the profile + set up frida (one command)
dexmachina console              # interactive pentest REPL (recommended)
dexmachina shell                # …or a raw subshell with every tool on PATH
```

Inside `dexmachina shell`, tools like `jadx`, `apktool`, `objection`, and
`frida` are directly on your `PATH`. Type `exit` to leave.

## Pentest a rooted emulator — full walkthrough

Assuming a rooted emulator/device is running with USB debugging (e.g. a
Genymotion / rooted AVD / Corellium instance, visible via `adb devices`):

```bash
# 0) one-time: build the dynamic-analysis kit (adb, frida, objection, …)
dexmachina up --profile dynamic

# 1) drop into the interactive console
dexmachina console
```

Then drive the engagement from the **DexMachina console**:

```text
dexmachina [no-device | no-target]> devices          # auto-selects a single device
dexmachina [emulator-5554 | no-target]> ready        # push + start frida-server
dexmachina [emulator-5554 | no-target]> apps owasp   # find your target (filter)
dexmachina [emulator-5554 | no-target]> target com.example.app
dexmachina [emulator-5554 | com.example.app]> status # device + frida + target summary
dexmachina [emulator-5554 | com.example.app]> proxy 10.0.2.2:8080   # route HTTPS to Burp
dexmachina [emulator-5554 | com.example.app]> hook   # SSL pinning + root bypass (spawn)
dexmachina [emulator-5554 | com.example.app]> objection             # interactive explorer
dexmachina [emulator-5554 | com.example.app]> logcat com.example.app   # watch logs
dexmachina [emulator-5554 | com.example.app]> exit
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
| `ps` / `run <tool> [args]` | List processes / run any DexMachina tool |
| `clear` · `help` · `exit` | Housekeeping |

Reproduce the exact kit on another machine:

```bash
dexmachina lock                 # write dexmachina.lock.toml (commit this)
# … teammate clones the repo …
dexmachina restore              # install the locked tools + frida runtime
```

## Quick Start

```bash
# One-command environment (auto-inits a repo-local workspace inside a git repo)
dexmachina up --profile dynamic

# See / inspect profiles
dexmachina profile list
dexmachina profile show static

# Drive an engagement interactively
dexmachina console              # pentest REPL with live device + target state

# Put every installed tool on PATH
dexmachina shell                # subshell (easiest)
dexmachina env                  # or print the PATH snippet for your shell

# Get a single tool, downloaded + on PATH + verified
dexmachina get jadx

# Get a device frida-ready in one shot (runtime + push-server + verify)
dexmachina device ready

# Check what's installed vs latest (use --offline to skip network)
dexmachina status --offline

# Diagnose / auto-repair
dexmachina doctor
dexmachina fix --bootstrap
```

### When to run `up`

Run `dexmachina up` when creating an environment, after cloning an engagement
workspace, or after changing its profile, pins, or lockfile. It is safe to run
again: tools and Frida environments that already satisfy the configuration are
skipped. Use `dexmachina update` for upgrades and `--force` only when you
intentionally want a reinstall.

For a normal daily pentest session, you usually only need:

```bash
dexmachina device ready          # reconnect/restart the matching frida-server
dexmachina console               # resume device + target workflow
```

## Commands

### Get started

| Command | Description |
|---------|-------------|
| `dexmachina init [--profile NAME] [--force]` | Create a repo-local workspace (config + `.gitignore` + `.dexmachina/tools`) |
| `dexmachina up [--profile NAME] [--no-frida] [--yes]` | Build the environment: install a profile + set up frida + write lockfile |
| `dexmachina console [--device SERIAL]` | Interactive pentest REPL with live device + target state |
| `dexmachina shell` | Open a subshell with every installed tool on `PATH` |
| `dexmachina profile list` / `show <name>` | List profiles or inspect a profile's tools |
| `dexmachina lock` | Write `dexmachina.lock.toml` from the current kit |
| `dexmachina restore [--yes]` | Install tools/frida exactly as recorded in the lockfile |

### Environment

| Command | Description |
|---------|-------------|
| `dexmachina status [--category NAME] [--offline]` | Table of installed vs latest versions |
| `dexmachina install <tool> [--version X.Y.Z] [--force]` | Install tool + dependencies |
| `dexmachina get <tool>` | Install a tool, put it on `PATH`, and verify it's runnable |
| `dexmachina install --all` | Install entire registry (topological order) |
| `dexmachina update [tool] [--all] [--force]` | Update to latest; pin groups update atomically |
| `dexmachina pin <tool> <version>` | Lock tool/pin-group version in config |
| `dexmachina unpin <tool>` | Remove version lock |
| `dexmachina env [--frida-only]` | Print PATH setup for all tools (or just the frida venv) |
| `dexmachina doctor` | Environment health report |
| `dexmachina fix [--dry-run] [--yes] [--bootstrap] [--aggressive]` | Diagnose and auto-repair issues |

### Device & arsenal

| Command | Description |
|---------|-------------|
| `dexmachina device list` | List connected ADB devices |
| `dexmachina device ready [--device SERIAL]` | Ensure frida runtime + push frida-server + verify with `frida-ps -U` |
| `dexmachina push-server [--device SERIAL] [--no-start]` | Push frida-server matching local frida |
| `dexmachina info [tool]` | Tool catalog, or detail card for one tool |
| `dexmachina arsenal` | List runnable tool CLIs (ready / missing) |
| `dexmachina run <tool> [args…]` | Run a tool via explicit dispatch |
| `dexmachina <tool> [args…]` | Direct dispatch (e.g. `dexmachina frida -U`) |
| `dexmachina config` | Show `dexmachina.toml` |
| `dexmachina config set <key> <value>` | Update a setting |

## Profiles

Profiles are curated tool bundles for one-command setup with `dexmachina up --profile NAME`:

| Profile | Tools |
|---------|-------|
| `minimal` | adb, frida, frida-tools |
| `dynamic` | frida stack, objection, r2frida, medusa |
| `static` | jadx, apktool, smali/baksmali, dex2jar, enjarify |
| `traffic` | mitmproxy, apk-mitm |
| `scanners` | MobSF, nuclei, drozer |
| `full` | everything auto-installable in the registry |

## Repo-local layout

`dexmachina init` produces a portable, reproducible workspace:

```text
my-repo/
├── dexmachina.toml         # committed — settings + profile + pins
├── dexmachina.lock.toml    # committed — exact installed versions (dexmachina lock)
├── .gitignore              # auto-updated to ignore downloaded tools
└── .dexmachina/
    ├── tools/              # downloaded CLIs/jars (gitignored)
    └── cache/              # PyPI/GitHub cache (gitignored)
```

Frida runtimes live in per-version venvs under `~/.dexmachina/venvs/` (machine-specific,
recreated by `dexmachina use` / `dexmachina restore`), so they're never committed.

## Configuration

`~/.dexmachina/dexmachina.toml` (or `./dexmachina.toml` in the project directory):

```toml
[settings]
adb_path = "adb"
java_path = "java"
install_dir = "~/.dexmachina/tools"
auto_push_frida_server = false

[pins]
frida = "16.1.4"   # pins the entire frida group

[ignored]
tools = ["ghidra", "wireshark"]
```

### Frida pin group (important)

The **frida runtime** (pip package `frida`) uses the version you care about for device hooks — e.g. `17.11.0`.

**frida-tools** and **objection** have **their own** pip version numbers (e.g. `14.9.0`, `1.12.5`) but must be compatible with the frida runtime. DexMachina never installs `frida-tools==17.11.0` — that was the old bug.

| Command | What it does |
|---------|----------------|
| `dexmachina use 17.11.0` | **nvm-style** — create/select isolated venv for this runtime |
| `dexmachina use latest` | Use latest frida release |
| `dexmachina sync frida` | Align global pip: exact frida + upgrade companions |
| `dexmachina pin frida 17.11.0` | Save preference in config (then `use` or `sync`) |
| `dexmachina versions frida` | Show active, pinned, installed, PyPI releases |
| `dexmachina env` | Print `PATH` snippet for active venv |

After `dexmachina use X`, run the `dexmachina env` output in your shell, then `dexmachina push-server`.

### Arsenal — run tools through DexMachina

Tools with a CLI are registered as native commands:

```bash
dexmachina arsenal              # ready vs missing
dexmachina frida --version
dexmachina frida-ps -U
dexmachina objection explore
dexmachina jadx --help
dexmachina run mitmproxy        # explicit form
```

Resolution order: **active frida venv** → `~/.dexmachina/tools/*/bin` → system `PATH`.

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

## `dexmachina fix`

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
| **High impact / manual** | DexMachina cannot apply automatically (upgrade Python, install JDK, plug in a device) |

Every `dexmachina fix` run prints a legend panel explaining these before the plan. Use `--no-legend` to hide it.

## Roadmap: Pentest Environment

DexMachina aims to become a batteries-included Android pentest environment:

- **Today** — tool registry, version pinning, doctor, fix, frida-server push
- **Next** — environment profiles (`minimal`, `dynamic`, `full`), PATH/setup shell hook, workspace templates
- **Future** — bundled configs (mitmproxy certs, MobSF docker compose), project scaffolds, CI-ready headless mode

## GitHub API

Release versions are fetched from the GitHub Releases API with a 1-hour cache in `~/.dexmachina/cache/`. Set `GITHUB_TOKEN` to avoid rate limits.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT

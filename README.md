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

On first run, DroidForge creates `~/.droidforge/droidforge.toml` from the bundled default template.

## Quick Start

```bash
# Check what's installed vs latest
droidforge status

# Install frida and its pin-group siblings
droidforge install frida

# Install everything (respects dependency order)
droidforge install --all

# Pin the frida group to a specific version
droidforge pin frida 16.1.4

# Push matching frida-server to a connected device
droidforge push-server

# Diagnose problems
droidforge doctor

# Auto-repair what we can (frida sync, adb, frida-server, broken installs)
droidforge fix

# Bootstrap the core pentest environment (missing adb, frida, jadx, apktool, …)
droidforge fix --bootstrap

# Preview fixes without applying
droidforge fix --dry-run
```

## Commands

| Command | Description |
|---------|-------------|
| `droidforge status [--category NAME]` | Table of installed vs latest versions |
| `droidforge install <tool> [--version X.Y.Z] [--force]` | Install tool + dependencies |
| `droidforge install --all` | Install entire registry (topological order) |
| `droidforge update [tool] [--all] [--force]` | Update to latest; pin groups update atomically |
| `droidforge pin <tool> <version>` | Lock tool/pin-group version in config |
| `droidforge unpin <tool>` | Remove version lock |
| `droidforge push-server [--device SERIAL] [--no-start]` | Push frida-server matching local frida |
| `droidforge doctor` | Environment health report |
| `droidforge fix [--dry-run] [--yes] [--bootstrap] [--aggressive]` | Diagnose and auto-repair issues |
| `droidforge info [tool]` | Tool catalog, or detail card for one tool |
| `droidforge arsenal` | List runnable tool CLIs (ready / missing) |
| `droidforge run <tool> [args…]` | Run a tool via explicit dispatch |
| `droidforge <tool> [args…]` | Direct dispatch (e.g. `droidforge frida -U`) |
| `droidforge config` | Show `droidforge.toml` |
| `droidforge config set <key> <value>` | Update a setting |

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

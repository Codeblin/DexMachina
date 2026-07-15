# Trust and Supply Chain Model

DexMachina manages Android pentest tools that can inspect devices, proxy traffic, and execute code. Treat it as security-sensitive workstation software.

## What DexMachina Downloads

Sources are declared in `dexmachina/registry.py`.

| Source type | Examples | Pinning model | Verification today |
| --- | --- | --- | --- |
| PyPI packages | `frida`, `frida-tools`, `objection`, `mitmproxy` | Optional exact versions through pins and lockfiles | TLS transport and pip's normal package validation |
| GitHub Releases | `jadx`, `apktool`, `scrcpy`, `nuclei` | Optional release version for some tools | TLS transport, archive extraction checks, SHA-256 verification when an upstream checksum asset or lockfile digest is available |
| Direct archives | Android platform-tools | URL selected by platform | TLS transport, incomplete-download rejection, optional registry or lockfile SHA-256 verification |
| Git clones or source zips | `medusa` | Default branch today | TLS transport, no commit pin by default yet |
| System package managers | `apt`, `brew` tools | Managed by OS/package manager | Delegated to the package manager |
| Manual tools | Burp Suite, Ghidra, Wireshark | User-managed | Outside DexMachina automation |

## Integrity Guarantees

DexMachina downloads to a temporary `.part` file and only moves the archive into place after the response size matches `Content-Length`. Downloaded artifact SHA-256 digests are recorded in tool install metadata and copied into `dexmachina.lock.toml`.

For direct downloads, the registry can provide `download_sha256`; when present, DexMachina verifies it before extraction and aborts on mismatch. For GitHub Release downloads, DexMachina looks for common upstream checksum assets such as `SHA256SUMS`, `checksums.txt`, or `<artifact>.sha256` and verifies the selected asset when a matching checksum is found. During `dexmachina restore`, lockfile SHA-256 values are enforced for direct and GitHub Release artifacts.

Archive extraction rejects members that would write outside the target extraction directory.

Current gaps:

- GitHub Release assets are checksum-verified only when upstream publishes a discoverable checksum file or when restoring from a lockfile that already contains a digest.
- Source-zip fallbacks for GitHub repositories are not pinned to a commit.
- Android platform-tools uses Google's `latest` URL; the archive digest is recorded in the lockfile, but the first install cannot be verified against a vendor-published checksum because Google does not publish a stable checksum at that URL.

Roadmap:

- Add more per-version checksums for registry entries where upstream publishes them.
- Prefer release tags or immutable commit SHAs over default-branch source zips.
- Add signature verification for upstreams that publish signatures.

## Credentials and Network Calls

DexMachina uses network access for:

- PyPI metadata and package installs
- GitHub Releases API calls
- GitHub clone/source downloads
- Direct vendor downloads such as Android platform-tools
- Package manager calls such as `apt`, `brew`, or `npm`

`GITHUB_TOKEN`, when set, is sent only as an Authorization header to the GitHub API/download requests made by DexMachina's GitHub helpers. It is not written to the lockfile or config by DexMachina.

There is no telemetry or analytics phone-home behavior. Release checks and package metadata lookups happen only to resolve versions, status, installs, and updates. Use commands like `dexmachina status --offline` when you need to avoid version-check network calls.

## Privileges

DexMachina should not require host root/admin privileges for normal repo-local use. Some system package manager actions may invoke `sudo` on Linux because `apt` requires it. Target devices may need root for Frida attach workflows; that is device-side privilege, not host privilege.

`dexmachina fix --aggressive` may update multiple registered tools. It should not delete engagement data, rewrite unrelated user files, or run privileged host commands except through explicit package-manager paths.

## Local Data Boundaries

DexMachina stores managed tools and cache data under the configured install directory, commonly `./.dexmachina/` for repo-local workspaces or `~/.dexmachina/` for global state. Commands such as `pull`, `screenshot`, proxy setup, and logcat operate locally unless the underlying tool is explicitly configured by the user to send data elsewhere.

Do not store client secrets, target app data, screenshots, or packet captures in a public repository. `.dexmachina/tools/` and cache directories are intended to be ignored by git.

## Reproducibility

`dexmachina.lock.toml` is a reproducibility and audit feature. Two users restoring from the same lockfile should converge on the same DexMachina-managed tool versions where upstream sources still provide the referenced artifacts. For direct and GitHub Release artifacts, recorded SHA-256 digests are enforced during restore so an upstream artifact changing under the same version fails closed instead of silently changing the environment.

For stronger chain-of-custody, keep the lockfile with engagement notes and record any manual tools, emulator image, device build, and Frida server architecture used during testing.

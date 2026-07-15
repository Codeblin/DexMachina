# Changelog

All notable changes to DexMachina are documented here. This project follows Semantic Versioning while it is pre-1.0, with minor releases allowed to refine CLI behavior.

## [0.1.0] - 2026-07-14

### Added

- Initial public alpha version marker.
- CI matrix across Ubuntu, macOS, and Windows.
- Android/ADB smoke test.
- Shell-only rooted emulator integration workflow compatible with owner-only Actions policies.
- Trust and supply-chain model documentation.
- Security policy and coordinated disclosure process.
- Contribution guide with registry extension instructions.
- Dependabot configuration for Python dependencies.
- Atomic direct downloads with incomplete-body rejection.
- Optional SHA-256 verification support for direct-download registry entries.
- GitHub Release checksum discovery for common upstream checksum assets.
- Lockfile artifact digest recording and restore-time digest enforcement.
- Safe archive extraction that rejects path traversal members.
- Release metadata validation and GitHub release workflow for `v*` tags.

### Known Gaps

- GitHub Release assets are checksum-verified only when upstream publishes a discoverable checksum file or a lockfile digest is available.
- Signature verification is not implemented yet.
- PyPI publication is still pending.

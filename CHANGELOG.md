# Changelog

All notable changes to DexMachina are documented here. This project follows Semantic Versioning while it is pre-1.0, with minor releases allowed to refine CLI behavior.

## [0.1.0] - 2026-07-14

### Added

- Initial public alpha version marker.
- CI matrix for Python 3.10, 3.11, and 3.12 across Ubuntu, macOS, and Windows.
- Pull request emulator smoke test for Android/ADB basics.
- Trust and supply-chain model documentation.
- Security policy and coordinated disclosure process.
- Contribution guide with registry extension instructions.
- Dependabot configuration for Python dependencies and GitHub Actions.
- Atomic direct downloads with incomplete-body rejection.
- Optional SHA-256 verification support for direct-download registry entries.

### Known Gaps

- Most GitHub Release assets are not signature-verified yet.
- Rooted Frida-ready emulator integration is not yet enforced in CI.
- PyPI publication is still pending.

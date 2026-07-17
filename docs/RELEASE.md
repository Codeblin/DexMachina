# Release Process

PinDroid releases are tag-driven.

## One-Time PyPI Setup

Create the PyPI project and configure Trusted Publishing before pushing the first release tag.

PyPI Trusted Publisher fields:

- PyPI project: `pindroid`
- Owner: `Codeblin`
- Repository: `PinDroid`
- Workflow: `release.yml`
- Environment: `pypi`

GitHub environment:

- Create environment `pypi` in repository settings.
- Require reviewer approval for the environment.
- Restrict deployment branches/tags to release tags if available.

This matches PyPI's Trusted Publishing model: GitHub Actions gets a short-lived OIDC token, PyPI validates that token against the configured publisher, and PyPI mints a short-lived upload token. No long-lived PyPI token is stored in GitHub.

## Cut A Release

1. Make sure `pyproject.toml`, `pindroid/__init__.py`, and `CHANGELOG.md` all reference the same version.
2. Run:

```bash
python scripts/verify_release.py v0.1.0
python -m pytest
```

3. Commit the release changes.
4. Tag and push:

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

The release workflow will:

- validate release metadata,
- run tests,
- build distributions,
- create a GitHub Release,
- publish to PyPI through Trusted Publishing.

## If Publishing Fails

- Confirm the PyPI Trusted Publisher fields match this repository and workflow exactly.
- Confirm the GitHub environment is named `pypi`.
- Confirm the workflow has `id-token: write`.
- Re-run the tag workflow after fixing configuration.

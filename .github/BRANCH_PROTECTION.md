# Branch Protection Checklist

These settings live in GitHub repository settings and cannot be enforced by files alone.

Protect `master`:

- Require a pull request before merging.
- Require approvals.
- Require review from Code Owners.
- Dismiss stale approvals when new commits are pushed.
- Require status checks to pass before merging.
- Required checks:
  - `Tests on ubuntu-latest`
  - `Tests on macos-latest`
  - `Tests on windows-latest`
  - `Android tools smoke test`
  - `Rooted emulator integration`
- Require branches to be up to date before merging.
- Block force pushes.
- Block deletions.
- Restrict who can push to matching branches.
- Do not allow administrators or repository owners to bypass these rules for normal development.

Recommended workflow:

- All changes land through PRs.
- Dependabot PRs are merged only after CI is green.
- Release tags are created from protected `master`.

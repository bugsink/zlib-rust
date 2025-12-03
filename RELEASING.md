# Releases

The Python package and Cargo package versions follow the exact pinned zlib-rs
version. Binding-only fixes use a Python `.postN` version without changing the
engine version. Keep Cargo.lock committed.

For each release:

1. Run formatting, clippy, the test suite against an installed release wheel,
   and source-distribution validation.
2. Commit and push main. Wait for every CI job at that exact commit to pass.
3. Create `v<version>` at that commit and publish a GitHub release. Include the
   upstream release notes and reference the source commit recorded in the
   published crate's `.cargo_vcs_info.json`.
4. Wait for the release workflow's platform wheels and source distribution.

Historical versions 0.5.3 through 0.6.7 build GitHub Actions artifacts only.
Their commit author and committer dates follow the crate publication dates.
The GitHub releases are reconstructed now; they do not represent past package
publication or past maintenance of these Python bindings.

PyPI publication is disabled until repository variable `PYPI_PUBLISHING` equals
`true`. Only versions at least 0.6.8 may publish, even after that switch is set.
Before enabling it, configure a PyPI Trusted Publisher with:

- Project: `zlib-rust`
- Owner: `bugsink`
- Repository: `zlib-rust`
- Workflow: `release.yml`
- GitHub environment: `pypi`

The matching GitHub environment can require a reviewer. No PyPI token belongs
in this repository. After setup, dispatch `release.yml` with the existing tag
to build and publish the first public release. A tag must match the version in
pyproject.toml; published tags must never move.

Missing upstream capabilities raise `NotImplementedError`. Tests for them use
strict expected failures with a precise reason and exception type. Remove the
expectation in the same upstream update that implements the capability.

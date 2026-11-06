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

Reconstructed versions 0.5.3 through 0.6.8 build GitHub Actions artifacts only.
The first public package version is 0.6.8.post2.
Their commit author and committer dates follow the crate publication dates.
The GitHub releases are reconstructed now; they do not represent past package
publication or past maintenance of these Python bindings.

Only versions at least 0.6.8.post2 may publish to PyPI. Publication waits for
approval from a required reviewer on the GitHub `pypi` environment.
The PyPI Trusted Publisher is configured with:

- Project: `zlib-rust`
- Owner: `bugsink`
- Repository: `zlib-rust`
- Workflow: `release.yml`
- GitHub environment: `pypi`

The matching GitHub environment requires a reviewer. No PyPI token belongs
in this repository. Dispatch `release.yml` with the existing tag to build and
queue publication for approval. A tag must match the version in
pyproject.toml; published tags must never move.

Missing upstream capabilities raise `NotImplementedError`. Tests for them use
strict expected failures with a precise reason and exception type. Remove the
expectation in the same upstream update that implements the capability.


Decompressor flush errors follow [CPython gh-156173](https://github.com/python/cpython/pull/156176).
urllib3's [corresponding fix](https://github.com/urllib3/urllib3/pull/5271)
stops flushing a decoder after discarding invalid trailing gzip data. These
are the upstream behaviors we align with. urllib3 2.8.0 predates its fix, so
the affected integration test has a strict expected failure until a released
urllib3 includes it.


## Automatic dependency releases

Dependabot checks the Rust dependencies daily, picking up zlib-rs immediately
and allowing three days for ordinary Rust updates. Test dependencies and
GitHub Actions are checked weekly. A Dependabot PR is squash-merged only after
its entire CI run passes for that exact PR head.

The merge workflow explicitly dispatches CI on the resulting main commit.
After those tests pass, CI calls the release check directly. Ordinary main
pushes start the same check through workflow_run. These explicit calls avoid
GitHub's restriction on starting workflows from events created by GITHUB_TOKEN.

The release check aligns package versions with the pinned engine, collects
dependency licenses, creates the tag and upstream release notes, and explicitly
dispatches the wheel workflow. A pending engine release is still recognized if
an unrelated commit followed the dependency update. Tooling-only changes do
not publish an already aligned engine version. Repeated checks reuse an
existing tag only when it points at the same source commit.

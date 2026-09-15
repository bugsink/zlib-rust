"""Read release notes and provenance for an exact published zlib-rs crate."""

import io
import json
import os
import tarfile
import urllib.error
import urllib.request


def release_notes(crate, version, reason):
    if crate != "zlib-rs":
        raise ValueError("only zlib-rs releases are supported")
    archive_url = f"https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
    with urllib.request.urlopen(archive_url) as response:
        data = response.read()
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        vcs = json.load(archive.extractfile(f"{crate}-{version}/.cargo_vcs_info.json"))
    commit = vcs["git"]["sha1"]
    request = urllib.request.Request(
        f"https://api.github.com/repos/trifectatechfoundation/zlib-rs/releases/tags/v{version}",
        headers={"Accept": "application/vnd.github+json"},
    )
    if os.environ.get("GH_TOKEN"):
        request.add_header("Authorization", "Bearer " + os.environ["GH_TOKEN"])
    try:
        with urllib.request.urlopen(request) as response:
            upstream = json.load(response)
        notes = upstream.get("body") or "Upstream did not supply release notes."
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        notes = "Upstream did not publish a GitHub release for this crate version."
    return (
        f"{reason}.\n\n"
        f"Crate source: https://github.com/trifectatechfoundation/zlib-rs/commit/{commit}\n\n"
        f"## Upstream release notes\n\n{notes}\n"
    )

"""Include the license texts for every locked Rust dependency."""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    metadata = json.loads(
        subprocess.check_output(
            ["cargo", "metadata", "--locked", "--format-version", "1"],
            cwd=ROOT,
        )
    )
    for package in metadata["packages"]:
        if package["source"] is None:
            continue
        source = Path(package["manifest_path"]).parent
        destination = ROOT / "licenses" / f"{package['name']}-{package['version']}"
        for path in source.iterdir():
            if path.is_file() and path.name.upper().startswith(
                ("LICENSE", "COPYING", "NOTICE")
            ):
                destination.mkdir(parents=True, exist_ok=True)
                (destination / path.name).write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()

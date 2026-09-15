"""Install the test extra without building the extension a second time."""

from pathlib import Path
import subprocess
import sys
import tomllib

metadata = tomllib.loads(
    (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()
)
requirements = metadata["project"]["optional-dependencies"]["test"]
subprocess.run([sys.executable, "-m", "pip", "install", *requirements], check=True)

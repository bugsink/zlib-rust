from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent / "upstream/cpython/harness"))


def pytest_addoption(parser):
    parser.addoption(
        "--bigmem", help="Memory budget for CPython's large-buffer tests, e.g. 8G"
    )


def pytest_configure(config):
    budget = config.getoption("--bigmem")
    if budget:
        from test import support

        support.set_memlimit(budget)


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.name != "test_zlib.py" or item.path.parent.name != "cpython":
            continue
        if item.name in {"test_compresscopy", "test_decompresscopy"}:
            item.add_marker(
                pytest.mark.xfail(
                    reason="upstream safe API does not expose stream copying",
                    raises=NotImplementedError,
                    strict=True,
                )
            )

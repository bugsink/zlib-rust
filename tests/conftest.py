from pathlib import Path
import sys

import pytest
import zlib_rust

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
        if (
            item.path.name == "test_decoders.py"
            and item.path.parent.name == "urllib3"
            and item.name == "test_chunked_decoding_gzip_swallow_garbage"
        ):
            item.add_marker(
                pytest.mark.xfail(
                    reason="urllib3 2.8.0 flushes discarded gzip garbage; upstream #5268/#5271",
                    raises=zlib_rust.error,
                    strict=True,
                )
            )
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

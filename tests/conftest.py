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
    import zlib_rust

    version = tuple(map(int, zlib_rust.ZLIB_RS_VERSION.split(".")))
    missing_dictionaries = {
        "test_dictionary",
        "test_dictionary_streaming",
        "test_decompress_raw_with_dictionary",
    }
    missing_configuration = {"test_compressoptions", "test_keywords"}
    for item in items:
        if item.path.name != "test_zlib.py" or item.path.parent.name != "cpython":
            continue
        reason = None
        if item.name in {"test_compresscopy", "test_decompresscopy"}:
            reason = "upstream safe API does not expose stream copying"
        elif version < (0, 5, 4) and item.name in missing_dictionaries:
            reason = "safe preset dictionaries require zlib-rs 0.5.4"
        elif (
            item.cls.__name__ == "CompressObjectTestCase"
            and item.name in missing_configuration
        ):
            reason = "upstream safe API does not expose memLevel/strategy configuration"
        if reason:
            item.add_marker(
                pytest.mark.xfail(
                    reason=reason, raises=NotImplementedError, strict=True
                )
            )
        if version < (0, 5, 4) and item.name == "test_wbits":
            item.add_marker(
                pytest.mark.xfail(
                    reason="detailed decoder error messages require zlib-rs 0.5.4",
                    raises=AssertionError,
                    strict=True,
                )
            )

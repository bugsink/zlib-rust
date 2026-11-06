# CPython

The zlib and gzip tests and the Python gzip implementation come from CPython
v3.14.0, commit `ebf955df7a89ed0c7968f79faec1de49f61ed7cb`:
<https://github.com/python/cpython/tree/ebf955df7a89ed0c7968f79faec1de49f61ed7cb>.
This is the Python release available when zlib-rs 0.5.3 was published.
The PSF license is included at `licenses/cpython/LICENSE`.

`test_zlib.py` and `test_gzip.py` retain their upstream assertions, with these
adaptations:

- Import `zlib_rust` and `zlib_rust.gzip` instead of the standard-library modules.
- Gzip command-line subprocesses invoke `zlib_rust.gzip` too, so they test the
  installed package rather than the standard library.
- Four Python 3.14 unittest assertions (`assertHasAttr` and `assertIsSubclass`)
  use equivalent `assertTrue(hasattr(...))` and `assertTrue(issubclass(...))`
  expressions, allowing the same tests to run on Python 3.11–3.13.
- Compute `is_s390x` using `platform.machine()` because the older test support
  harness does not export that constant.

The test support package is copied from CPython v3.13.0, commit
`60403a5409ff2c3f3b07dd2ca91a7a3e096839c7`, without changes. Using this version
avoids Python 3.14-only dependencies in the test harness. It is added only to
the test process's import path and is not shipped in wheels.

The upstream resource gates remain: tests requiring several GiB of memory do
not run without an explicit memory budget (`pytest --bigmem=8G`); the reference-count leak test
requires a debug interpreter. There are no additional blanket skips.

Expected failures are declared centrally in `tests/conftest.py`, restricted to
specific tests and exception types, and strict: an unexpected pass fails CI.
In 0.5.3 dictionaries and detailed decoder errors are not exposed by the safe
API. Non-default compression configuration is unavailable through 0.6.7; 0.6.8
adds it and removes those expectations. Stream copying remains unavailable. Successful format/window combinations are separately tested in
the project suite so the error-message expectation does not hide their behavior.

`python/zlib_rust/gzip.py` and `_gzip_streams.py` are copied from `Lib/gzip.py`
and `Lib/compression/_common/_streams.py` at the same v3.14.0 commit. Gzip imports
our codec and its local copy of the stream helpers. Its CLI omits the Python
3.14-only argparse `color` keyword. Codec and file-format behavior is unchanged.

Two additional tests, `test_decompress_flush_corrupt_stream` and
`test_decompress_flush_twice`, are copied unchanged from CPython commit
`54426877bd7ea4e532f5d531a2958d5aa1c29f7c` ([gh-156173](https://github.com/python/cpython/pull/156176)).
They cover the newer behavior where flush reports corrupt input instead of
silently returning output. This fixes behavior present in the v3.14.0 baseline.

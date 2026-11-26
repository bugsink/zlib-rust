# CPython

The zlib tests, gzip implementation, stream helpers and gzip tests come from CPython main,
commit `b0b000527e895a2882259a6a4b5bdfbf5618c54a` (2026-11-26):
<https://github.com/python/cpython/tree/b0b000527e895a2882259a6a4b5bdfbf5618c54a>.
The source files are `Lib/test/test_zlib.py`, `Lib/gzip.py`,
`Lib/compression/_common/_streams.py` and `Lib/test/test_gzip.py`.
The PSF license is included at `licenses/cpython/LICENSE`.

`test_zlib.py` and `test_gzip.py` retain their upstream assertions, with these
adaptations for this package and Python 3.11 or newer:

- Import `zlib_rust` and `zlib_rust.gzip` instead of the standard-library modules.
- Gzip command-line subprocesses invoke `zlib_rust.gzip` too, so they test the
  installed package rather than the standard library.
- Python 3.14 unittest assertions (`assertHasAttr` and `assertIsSubclass`)
  use equivalent `assertTrue(hasattr(...))` and `assertTrue(issubclass(...))`
  expressions, allowing the same tests to run on Python 3.11–3.13.
- Compute `is_s390x` using `platform.machine()` because the older test support
  harness does not export that constant.
- Omit `TestModule.test_deprecated_module_attributes`: CPython deprecates its
  fixed `zlib.__version__ == "1.0"`, whereas this independently released package
  uses `__version__` for its package version.
- Omit `VersionTestCase.test_zlibng_version` and its helper: this package uses
  zlib-rs, so zlib-ng metadata is inapplicable. The zlib library-version
  assertions remain unchanged, including Python 3.16's structured version
  information.
- The gzip CLI tests disable color through environment variables instead of
  `force_not_colorized_test_class`, which the older test harness lacks.
- Gzip's implicit write-mode tests include `wb+`, `ab+` and `xb+` only on
  Python 3.15 or newer. Earlier interpreters report these modes as `rb+`, so
  gzip cannot distinguish them from a file opened for reading. This follows
  CPython [gh-69528 / GH-137834](https://github.com/python/cpython/pull/137834).

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

`python/zlib_rust/gzip.py` imports our codec and its local copy of the stream
helpers. Its CLI uses `runpy._remove_sys_path0()` where available. On older
interpreters it removes copies of the initial `sys.path[0]` directly, unless
safe-path mode is enabled or that path is the standard-library directory.
Those interpreters do not expose the original path through `sys._path0`.
`_gzip_streams.py` is copied without changes.

The zlib test baseline includes the fixes for corrupt-stream flush errors
([gh-156173 / GH-156176](https://github.com/python/cpython/pull/156176)),
clearing `unconsumed_tail` at EOF
([gh-158169 / GH-158177](https://github.com/python/cpython/pull/158177)), and
negative checksum-combine lengths
([gh-156180 / GH-156181](https://github.com/python/cpython/pull/156181)).

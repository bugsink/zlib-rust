# zlib-rust

Python bindings for [zlib-rs](https://github.com/trifectatechfoundation/zlib-rs).
Use the zlib API independently of the library chosen by your Python distributor:

```python
import zlib_rust as zlib

compressed = zlib.compress(b"hello")
assert zlib.decompress(compressed) == b"hello"
```

File-oriented gzip support uses CPython's Python implementation with the Rust
codec underneath:

```python
from zlib_rust.gzip import GzipFile
```

The binding forbids unsafe Rust and releases the GIL during codec operations.
The underlying zlib-rs engine does contain unsafe Rust. Immutable Python bytes
are borrowed without an input copy; other contiguous buffers are copied before
processing so another thread cannot mutate their contents during processing.

This version follows zlib-rs 0.5.3. Preset dictionaries, non-default compression
memory/strategy settings, and stream copying raise `NotImplementedError` because
the upstream safe API does not expose them. Both checksum-combine functions are
available on every supported Python version. `ZLIB_RS_VERSION` identifies the
engine; `ZLIB_VERSION` and `ZLIB_RUNTIME_VERSION` identify its compatible zlib API.

Development uses Rust 1.85 or newer, Python 3.11 or newer, maturin, and pytest.
Build an installed wheel with `maturin build --release --locked`, install that
wheel, then run `pytest`. Imported tests retain their licenses and exact source
references under `tests/upstream/`.

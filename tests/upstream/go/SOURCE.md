# Go DEFLATE tests

Source: Go 1.25.3, commit `28622c19591d95c9a83f706f2ed1b303d58da85f`:
<https://github.com/golang/go/tree/28622c19591d95c9a83f706f2ed1b303d58da85f/src/compress/flate>.
The Go BSD license is copied unchanged as `LICENSE`.

`test_flate.py` is a Python adaptation, not an unchanged copy of the Go tests:

- All 28 `TestStreams` descriptions, compressed bytes, and expected output or
  failure results from `flate_test.go` are retained. The Python harness runs
  each vector both in one call and with one-byte input chunks and a seven-byte
  output limit. The latter adds checks for bounded output and forward progress.
  Go errors become `zlib_rust.error` expectations.
- The ten input/output pairs from `inflate_test.go::TestReaderTruncated` are
  retained byte-for-byte, including Go strings containing both UTF-8 text and
  byte escapes. Python's streaming API returns the decoded prefix and leaves
  `eof` false rather than raising Go's `io.ErrUnexpectedEOF`. We assert both
  the original expected prefix and that state, and separately require one-shot
  decompression to raise for the incomplete stream.
- `flate_test.go::TestTruncatedStreams` retains the original stream and truncation
  range (all prefixes shorter than `len(data) - 1`). Python's exception replaces
  Go's `io.ErrUnexpectedEOF` assertion.
- `reader_test.go::TestNlitOutOfRange` retains the malformed bytes. Upstream only
  requires that decoding not panic and discards the error; the adaptation also
  requires `zlib_rust.error` for this invalid literal-count header.

Go's tests of internal Huffman constructors and reader reset/buffer reuse are
not ported: our public Python API does not expose those operations.

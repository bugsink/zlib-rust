# zlib-rs regression fixtures

Source: the published zlib-rs 0.6.8 crate's recorded source commit,
`0254e07204884bfc902d6ebb68c8b703d0ea49cf`:
<https://github.com/trifectatechfoundation/zlib-rs/tree/0254e07204884bfc902d6ebb68c8b703d0ea49cf/test-libz-rs-sys/src>.
The upstream zlib license is included as `LICENSE`.

The three `.gz` files are unmodified copies from `test-data/`. The Python tests
adapt the stream-decoding checks to the public binding. `issue-109.gz` is decoded
with small output buffers and checked against the independent C decoder. The
two malformed stack-overflow regressions are checked with their original zlib
configuration, and also with format autodetection to exercise the gzip header
of the second fixture. No callback-only `inflateBack` API is claimed here.

`corpus/` contains the six unmodified gzip vectors used by upstream's
`infback::various` test. These cover stored data and the default, filtered,
Huffman-only, fixed-Huffman, and run-length compression strategies. The adapted
test decodes them with small input and output buffers and compares the result
with the independent C decoder; it does not expose `inflateBack`.

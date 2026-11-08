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

Additional regressions from `inflate.rs` at that same source commit:

- `window_match_bug`: unmodified `window-match-bug.zraw`, with the original
  `wbits=-10` and 402-byte output limit.
- `op_len_edge_case`: unmodified `op-len-edge-case.zraw`, with the original
  `wbits=-9` and 266-byte output limit. Its unmodified `.dat` file provides the
  original uncompressed bytes as an additional independent expectation.
- `chunked_output_rs`: the same seven compressed bytes, a 32-byte output call,
  then a one-byte call that must finish the 33-byte stream.

The Python adaptations check the decoded bytes against the independent C
codec, output limits, forward progress, and final EOF. They use public
`decompress()` calls instead of the original C return-code loops. In particular,
`window_match_bug` uses `InflateFlush::Finish` upstream; Python's public
`decompress()` does not expose that flush parameter, so that exact low-level
call sequence is not claimed here.

`test_low_memory_compression_regressions` adapts the three cases in
[`zlib_ng_cve.rs`](https://github.com/trifectatechfoundation/zlib-rs/blob/0254e07204884bfc902d6ebb68c8b703d0ea49cf/test-libz-rs-sys/src/zlib_ng_cve.rs).
The `zlib-ng/` files are unmodified copies of its historical zlib/zlib-ng
regression inputs. Window size 15, memory level 1, default compression level,
and default strategy are retained. Instead of comparing compressed bytes with
zlib-ng as upstream does, the Python adaptation checks that the independent C
zlib decoder recovers the original input. It does not claim to reproduce a
memory-sanitizer check or prove the absence of low-level memory errors.

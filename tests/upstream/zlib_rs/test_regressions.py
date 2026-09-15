from pathlib import Path
import zlib as cpython_zlib

import pytest
import zlib_rust as zlib

ROOT = Path(__file__).parent


def test_issue_109_with_small_output_buffers():
    data = (ROOT / "issue-109.gz").read_bytes()
    expected = cpython_zlib.decompress(data, 31)
    decoder = zlib.decompressobj(31)
    chunks = []
    pending = data
    while not decoder.eof:
        chunks.append(decoder.decompress(pending, 256))
        pending = decoder.unconsumed_tail
    assert b"".join(chunks) == expected


@pytest.mark.parametrize(
    "filename", ["blow_up_the_stack_1.gz", "blow_up_the_stack_2.gz"]
)
@pytest.mark.parametrize("wbits", [15, 47])
def test_malformed_stack_regressions(filename, wbits):
    data = (ROOT / filename).read_bytes()
    with pytest.raises(cpython_zlib.error):
        cpython_zlib.decompress(data, wbits)
    with pytest.raises(zlib.error):
        zlib.decompress(data, wbits)


@pytest.mark.parametrize(
    "strategy", ["0", "9", "filtered-9", "huffman-9", "fixed-9", "rle-9"]
)
def test_upstream_compression_strategies(strategy):
    path = ROOT / "corpus" / ("The fastest WASM zlib.md.gzip-" + strategy + ".gz")
    data = path.read_bytes()
    expected = cpython_zlib.decompress(data, 31)
    decoder = zlib.decompressobj(31)
    chunks = []
    for offset in range(0, len(data), 113):
        pending = data[offset : offset + 113]
        while pending:
            chunks.append(decoder.decompress(pending, 257))
            pending = decoder.unconsumed_tail
    while not decoder.eof:
        part = decoder.decompress(b"", 257)
        assert part, "complete input must finish or produce output"
        chunks.append(part)
    assert b"".join(chunks) == expected

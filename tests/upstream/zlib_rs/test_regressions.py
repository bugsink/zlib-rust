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


@pytest.mark.parametrize(
    "filename, wbits, limit",
    [("window-match-bug.zraw", -10, 402), ("op-len-edge-case.zraw", -9, 266)],
)
def test_small_window_regressions(filename, wbits, limit):
    data = (ROOT / filename).read_bytes()
    expected = cpython_zlib.decompress(data, wbits)
    if filename == "op-len-edge-case.zraw":
        assert expected == (ROOT / "op-len-edge-case.dat").read_bytes()
    decoder = zlib.decompressobj(wbits)
    chunks = []
    pending = data
    while not decoder.eof:
        chunk = decoder.decompress(pending, limit)
        assert len(chunk) <= limit
        chunks.append(chunk)
        remainder = decoder.unconsumed_tail
        assert chunk or decoder.eof or len(remainder) < len(pending)
        pending = remainder
    assert b"".join(chunks) == expected


def test_last_byte_after_full_output_buffer():
    # Upstream chunked_output_rs: a 32-byte output buffer, then the final byte.
    data = bytes([99, 96, 192, 11, 24, 25, 0])
    expected = cpython_zlib.decompress(data, -15)
    assert len(expected) == 33
    decoder = zlib.decompressobj(-15)
    first = decoder.decompress(data, 32)
    assert first == expected[:32]
    assert not decoder.eof
    last = decoder.decompress(decoder.unconsumed_tail, 1)
    assert last == expected[32:]
    assert decoder.eof


@pytest.mark.parametrize(
    "filename",
    [
        "zlib-ng/CVE-2018-25032/default.txt",
        "zlib-ng/CVE-2018-25032/fixed.txt",
        "zlib-ng/GH-382/defneg3.dat",
    ],
)
def test_low_memory_compression_regressions(filename):
    data = (ROOT / filename).read_bytes()
    encoder = zlib.compressobj(wbits=15, memLevel=1)
    compressed = encoder.compress(data) + encoder.flush()
    assert cpython_zlib.decompress(compressed) == data

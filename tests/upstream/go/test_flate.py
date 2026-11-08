# Copyright 2009 The Go Authors. All rights reserved.
# Copyright 2012 The Go Authors. All rights reserved.
# Copyright 2014 The Go Authors. All rights reserved.
# Adapted from Go compress/flate tests; see SOURCE.md and LICENSE.

import pytest
import zlib_rust as zlib

STREAMS = [
    pytest.param(
        "05e0010000000000100000000000000000000000000000000000000000000000"
        "00000000000000000004",
        "fail",
        id="degenerate HCLenTree",
    ),
    pytest.param(
        "05e0010400000000000000000000000000000000000000000000000000000000"
        "00000000000000000010",
        "fail",
        id="complete HCLenTree, empty HLitTree, empty HDistTree",
    ),
    pytest.param(
        "05e0010000000000000000000000000000000000000000000000000000000000"
        "00000000000000000010",
        "fail",
        id="empty HCLenTree",
    ),
    pytest.param(
        "000100feff000de0010400000000100000000000000000000000000000000000"
        "0000000000000000000000000000002c",
        "fail",
        id="complete HCLenTree, complete HLitTree, empty HDistTree, use missing HDist symbol",
    ),
    pytest.param(
        "000100feff000de0010000000000000000000000000000000000000000000000"
        "00000000000000000610000000004070",
        "fail",
        id="complete HCLenTree, complete HLitTree, degenerate HDistTree, use missing HDist symbol",
    ),
    pytest.param(
        "05e0010400000000100400000000000000000000000000000000000000000000"
        "0000000000000000000000000008",
        "fail",
        id="complete HCLenTree, empty HLitTree, empty HDistTree",
    ),
    pytest.param(
        "05e0010400000000100400000000000000000000000000000000000000000000"
        "0000000000000000000800000008",
        "fail",
        id="complete HCLenTree, empty HLitTree, degenerate HDistTree",
    ),
    pytest.param(
        "05e0010400000000100000000000000000000000000000000000000000000000"
        "0000000000000000001c",
        "fail",
        id="complete HCLenTree, degenerate HLitTree, degenerate HDistTree, use missing HLit symbol",
    ),
    pytest.param(
        "edff870500000000200400000000000000000000000000000000000000000000"
        "000000000000000000080000000000000004",
        "fail",
        id="complete HCLenTree, complete HLitTree, too large HDistTree",
    ),
    pytest.param(
        "edfd870500000000200400000000000000000000000000000000000000000000"
        "000000000000000000e8b100",
        "fail",
        id="complete HCLenTree, complete HLitTree, empty HDistTree, excessive repeater code",
    ),
    pytest.param(
        "05fd01240000000000f8ffffffffffffffffffffffffffffffffffffffffffff"
        "ffffffffffffffffff07000000fe01",
        "",
        id="complete HCLenTree, complete HLitTree, empty HDistTree of normal length 30",
    ),
    pytest.param(
        "05fe01240000000000f8ffffffffffffffffffffffffffffffffffffffffffff"
        "ffffffffffffffffff07000000fc03",
        "fail",
        id="complete HCLenTree, complete HLitTree, empty HDistTree of excessive length 31",
    ),
    pytest.param(
        "05e001240000000000fcffffffffffffffffffffffffffffffffffffffffffff"
        "ffffffffffffffffff07f00f",
        "fail",
        id="complete HCLenTree, over-subscribed HLitTree, empty HDistTree",
    ),
    pytest.param(
        "05e001240000000000fcffffffffffffffffffffffffffffffffffffffffffff"
        "fffffffffcffffffff07f00f",
        "fail",
        id="complete HCLenTree, under-subscribed HLitTree, empty HDistTree",
    ),
    pytest.param(
        "05e001240000000000f8ffffffffffffffffffffffffffffffffffffffffffff"
        "ffffffffffffffffff07f00f",
        "01",
        id="complete HCLenTree, complete HLitTree with single code, empty HDistTree",
    ),
    pytest.param(
        "05e301240000000000f8ffffffffffffffffffffffffffffffffffffffffffff"
        "ffffffffffffffffff07807f",
        "01",
        id="complete HCLenTree, complete HLitTree with multiple codes, empty HDistTree",
    ),
    pytest.param(
        "000100feff000de0010400000000100000000000000000000000000000000000"
        "0000000000000000000000000000003c",
        "00000000",
        id="complete HCLenTree, complete HLitTree, degenerate HDistTree, use valid HDist symbol",
    ),
    pytest.param(
        "05e0010400000000100000000000000000000000000000000000000000000000"
        "0000000000000000000c",
        "",
        id="complete HCLenTree, degenerate HLitTree, degenerate HDistTree",
    ),
    pytest.param(
        "05e0010400000000100000000000000000000000000000000000000000000000"
        "00000000000000000004",
        "",
        id="complete HCLenTree, degenerate HLitTree, empty HDistTree",
    ),
    pytest.param(
        "edfd870500000000200400000000000000000000000000000000000000000000"
        "000000000000000000e8b000",
        "",
        id="complete HCLenTree, complete HLitTree, empty HDistTree, spanning repeater code",
    ),
    pytest.param(
        "ede0010400000000100000000000000000000000000000000000000000000000"
        "0000000000000000000400004000",
        "",
        id="complete HCLenTree with length codes, complete HLitTree, empty HDistTree",
    ),
    pytest.param(
        "000100feff00ede0010400000000100000000000000000000000000000000000"
        "000000000000000000000000000000040000407f00",
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "000000",
        id="complete HCLenTree, complete HLitTree, degenerate HDistTree, use valid HLit symbol 284 with count 31",
    ),
    pytest.param(
        "0cc2010d00000082b0ac4aff0eb07d27060000ffff",
        "616263616263",
        id="complete HCLenTree, complete HLitTree, degenerate HDistTree, use valid HLit and HDist symbols",
    ),
    pytest.param(
        "33180700",
        "fail",
        id="fixed block, use reserved symbol 287",
    ),
    pytest.param(
        "010100feff11",
        "11",
        id="raw block",
    ),
    pytest.param(
        "344c4a4e494d4b070000ff2e2eff2e2e2e2e2eff",
        "fail",
        id="issue 10426 - over-subscribed HCLenTree causes a hang",
    ),
    pytest.param(
        "05c0070600000080400fff37a0ca",
        "",
        id="issue 11030 - empty HDistTree unexpectedly leads to error",
    ),
    pytest.param(
        "050fb109c020cca5d017dcbca044881ee1034ec149c8980bbc413c2ab35be9dc"
        "b1473449922449922411202306ee97b0383a521b4ffdcf3217f9f7d3adb701",
        "3130303634342068652e706870005d05355f7ed957ff084a90925d19e3ebc6d0c6d7",
        id="issue 11033 - empty HDistTree unexpectedly leads to error",
    ),
]


def _decompress_whole(data):
    return zlib.decompress(data, -15)


def _decompress_in_chunks(data):
    decoder = zlib.decompressobj(-15)
    chunks = []
    for byte in data:
        pending = bytes([byte])
        while pending:
            chunk = decoder.decompress(pending, 7)
            assert len(chunk) <= 7
            chunks.append(chunk)
            remainder = decoder.unconsumed_tail
            assert chunk or len(remainder) < len(pending), "decoder made no progress"
            pending = remainder
    while not decoder.eof:
        chunk = decoder.decompress(b"", 7)
        assert chunk, "complete input must finish or produce output"
        chunks.append(chunk)
    return b"".join(chunks)


@pytest.mark.parametrize("stream, want", STREAMS)
@pytest.mark.parametrize(
    "decompress",
    [_decompress_whole, _decompress_in_chunks],
    ids=["whole", "incremental"],
)
def test_streams(stream, want, decompress):
    data = bytes.fromhex(stream)
    if want == "fail":
        with pytest.raises(zlib.error):
            decompress(data)
    else:
        assert decompress(data) == bytes.fromhex(want)


@pytest.mark.parametrize(
    "data, expected",
    [
        (b"\x00", b""),
        (b"\x00\x0c", b""),
        (b"\x00\x0c\x00", b""),
        (b"\x00\x0c\x00\xf3\xff", b""),
        (b"\x00\x0c\x00\xf3\xffhello", b"hello"),
        (b"\x00\x0c\x00\xf3\xffhello, world", b"hello, world"),
        (b"\x02", b""),
        (b"\xf2H\xcd", b"He"),
        (b"\xf2H\xcd\x990a\xc2\x84\t", b"Hel\x90\x90\x90\x90\x90"),
        (b"\xf2H\xcd\x990a\xc2\x84\t\x00", b"Hel\x90\x90\x90\x90\x90"),
    ],
)
def test_reader_truncated(data, expected):
    decoder = zlib.decompressobj(-15)
    assert decoder.decompress(data) == expected
    assert not decoder.eof
    with pytest.raises(zlib.error):
        zlib.decompress(data, -15)


TRUNCATED_STREAM = b"\x00\x0c\x00\xf3\xffhello, world\x01\x00\x00\xff\xff"


@pytest.mark.parametrize("length", range(len(TRUNCATED_STREAM) - 1))
def test_truncated_streams(length):
    with pytest.raises(zlib.error):
        zlib.decompress(TRUNCATED_STREAM[:length], -15)


def test_nlit_out_of_range():
    # A Huffman table with nlit=288 must be rejected without a panic.
    data = bytes.fromhex(
        "fcfe36e75e1cefb3555877b656b543f46ff2d2e63d99a0858c48ebf8da83042a"
        "75c4f80f1211b9b44b09a0be8b914c"
    )
    with pytest.raises(zlib.error):
        zlib.decompress(data, -15)

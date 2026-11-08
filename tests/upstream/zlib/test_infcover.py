# Copyright (C) 2011, 2016, 2024 Mark Adler
# Adapted from zlib test/infcover.c; see SOURCE.md and LICENSE.

import re
import zlib as cpython_zlib

import pytest
import zlib_rust as zlib

INVALID_STREAMS = [
    pytest.param(
        "1f8b0000",
        31,
        "",
        id="bad gzip method",
    ),
    pytest.param(
        "1f8b0880",
        31,
        "",
        id="bad gzip flags",
    ),
    pytest.param(
        "7785",
        15,
        "",
        id="bad zlib method",
    ),
    pytest.param(
        "789c",
        8,
        "",
        id="bad zlib window size",
    ),
    pytest.param(
        "1f8b081e00000000000001000000000000",
        47,
        "",
        id="bad header crc",
    ),
    pytest.param(
        "7890",
        47,
        "",
        id="bad zlib header check",
    ),
    pytest.param(
        "08b800000001",
        8,
        "",
        id="need dictionary",
    ),
    pytest.param(
        "0000000000",
        -15,
        "invalid stored block lengths",
        id="invalid stored block lengths",
    ),
    pytest.param(
        "06",
        -15,
        "invalid block type",
        id="invalid block type",
    ),
    pytest.param(
        "fc0000",
        -15,
        "too many length or distance symbols",
        id="too many length or distance symbols",
    ),
    pytest.param(
        "0400feff",
        -15,
        "invalid code lengths set",
        id="invalid code lengths set",
    ),
    pytest.param(
        "0400244900",
        -15,
        "invalid bit length repeat",
        id="invalid bit length repeat",
    ),
    pytest.param(
        "040024e9ffff",
        -15,
        "invalid bit length repeat",
        id="invalid bit length repeat",
    ),
    pytest.param(
        "040024e9ff6d",
        -15,
        "invalid code -- missing end-of-block",
        id="invalid code -- missing end-of-block",
    ),
    pytest.param(
        "048049922449922471ffff931100",
        -15,
        "invalid literal/lengths set",
        id="invalid literal/lengths set",
    ),
    pytest.param(
        "04804992244992240fb4ffffc384",
        -15,
        "invalid distances set",
        id="invalid distances set",
    ),
    pytest.param(
        "04c0810800000000207feb0b0000",
        -15,
        "invalid literal/length code",
        id="invalid literal/length code",
    ),
    pytest.param(
        "027effff",
        -15,
        "invalid distance code",
        id="invalid distance code",
    ),
    pytest.param(
        "0cc081000000000090ff6b0400",
        -15,
        "invalid distance too far back",
        id="invalid distance too far back",
    ),
    pytest.param(
        "1f8b0800000000000000030000000001",
        47,
        "incorrect data check",
        id="incorrect data check",
    ),
    pytest.param(
        "1f8b080000000000000003000000000000000001",
        47,
        "incorrect length check",
        id="incorrect length check",
    ),
    pytest.param(
        "e5e081ad6dcbb22cc9011e5963ae7deefb4dfdb5354168ff7f0f000000",
        -8,
        "",
        id="fast length extra bits",
    ),
    pytest.param(
        "25fd81b56d59b66a49eaaf350634eb8cb9f6b91eef674950feffff3f0000",
        -8,
        "",
        id="fast distance extra bits",
    ),
    pytest.param(
        "037e0000000000",
        -8,
        "",
        id="fast invalid distance code",
    ),
    pytest.param(
        "1b070000000000",
        -8,
        "",
        id="fast invalid literal/length code",
    ),
    pytest.param(
        "0dc701aeeb380c0441a08772dedffb1fb836b1385dffff00",
        -8,
        "",
        id="fast 2nd level codes and too far back",
    ),
]

VALID_STREAMS = [
    pytest.param(
        "0899",
        0,
        0,
        1,
        False,
        id="set window size from header",
    ),
    pytest.param(
        "789c63000000010001",
        0,
        15,
        1,
        True,
        id="check adler32",
    ),
    pytest.param(
        "1f8b08020000000000001d2603000000000000000000",
        0,
        47,
        1,
        True,
        id="check gzip length",
    ),
    pytest.param(
        "789c6300",
        0,
        15,
        1,
        False,
        id="compute adler32",
    ),
    pytest.param(
        "0300",
        0,
        -15,
        257,
        True,
        id="fixed",
    ),
    pytest.param(
        "010100feff00",
        0,
        -15,
        257,
        True,
        id="stored",
    ),
    pytest.param(
        "05c0210d00000080b0fe6d2f916c",
        0,
        -15,
        257,
        True,
        id="pull 17",
    ),
    pytest.param(
        "05e0819124cbb22c49e20f2e8b9a47569ffbfeecd2ff1f",
        0,
        -15,
        257,
        True,
        id="long code",
    ),
    pytest.param(
        "edc001010000004020ff571b422c4f",
        0,
        -15,
        257,
        True,
        id="length extra",
    ),
    pytest.param(
        "edcfc1b12c4710c430fa6f351d0182593dfbbe2e2afc0f0c",
        0,
        -15,
        257,
        True,
        id="long distance and extra",
    ),
    pytest.param(
        "edc0810000000080a0fda917a900000000000000000000000000000000000000"
        "0000000000000000000000000006",
        0,
        -15,
        257,
        True,
        id="window end",
    ),
    pytest.param(
        "02082080000300",
        0,
        -15,
        258,
        True,
        id="inflate_fast TYPE return",
    ),
    pytest.param(
        "631805400c00",
        3,
        -8,
        300,
        True,
        id="window wrap",
    ),
    pytest.param(
        "6318058c100800000000",
        0,
        -8,
        259,
        True,
        id="very common case",
    ),
    pytest.param(
        "63606018c9000818181826c0280029000000",
        6,
        -8,
        259,
        True,
        id="contiguous and wrap around window",
    ),
    pytest.param(
        "6300030000000000",
        0,
        -8,
        259,
        True,
        id="copy direct from output",
    ),
]


@pytest.mark.parametrize("data, wbits, message", INVALID_STREAMS)
@pytest.mark.parametrize("incremental", [False, True], ids=["whole", "incremental"])
def test_invalid_streams(data, wbits, message, incremental):
    data = bytes.fromhex(data)
    with pytest.raises(zlib.error, match=re.escape(message) if message else None):
        if incremental:
            decoder = zlib.decompressobj(wbits)
            for byte in data:
                decoder.decompress(bytes([byte]))
        else:
            zlib.decompress(data, wbits)


@pytest.mark.parametrize("data, step, wbits, limit, eof", VALID_STREAMS)
def test_valid_streams_with_bounded_output(data, step, wbits, limit, eof):
    data = bytes.fromhex(data)
    reference = cpython_zlib.decompressobj(wbits)
    expected = reference.decompress(data)
    assert reference.eof == eof

    decoder = zlib.decompressobj(wbits)
    chunks = []
    step = step or len(data)
    for offset in range(0, len(data), step):
        pending = data[offset : offset + step]
        while pending:
            chunk = decoder.decompress(pending, limit)
            assert len(chunk) <= limit
            chunks.append(chunk)
            remainder = decoder.unconsumed_tail
            assert chunk or len(remainder) < len(pending), "decoder made no progress"
            pending = remainder
    while not decoder.eof:
        chunk = decoder.decompress(b"", limit)
        if not chunk:
            break
        assert len(chunk) <= limit
        chunks.append(chunk)
    assert decoder.eof == eof
    assert b"".join(chunks) == expected

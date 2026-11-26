import zlib as stdlib_zlib

from hypothesis import given, settings, strategies as st

import zlib_rust as zlib


@settings(deadline=None)
@given(
    pattern=st.binary(min_size=1, max_size=64),
    length=st.sampled_from([0, 1, 36, 37, 38, 8191, 8192, 8193, 16384]),
    input_size=st.sampled_from([1, 7, 127, 8192]),
    output_size=st.sampled_from([1, 37, 8192]),
    formats=st.sampled_from(
        [(-15, -15), (0, 15), (15, 15), (16, 31), (31, 31), (32, 15), (32, 31)]
    ),
    flush=st.sampled_from([stdlib_zlib.Z_SYNC_FLUSH, stdlib_zlib.Z_FULL_FLUSH]),
    initial=st.integers(min_value=0, max_value=100),
)
def test_gzip_decoder_preserves_data_across_stream_boundaries(
    pattern, length, input_size, output_size, formats, flush, initial
):
    payload = (pattern * (length // len(pattern) + 1))[:length]
    wbits, format_wbits = formats
    encoder = stdlib_zlib.compressobj(wbits=format_wbits)
    split = min(length, output_size)
    compressed = encoder.compress(payload[:split]) + encoder.flush(flush)
    compressed += encoder.compress(payload[split:]) + encoder.flush()
    compressed += b"next message"
    decoder = zlib._ZlibDecompressor(wbits)
    offset = min(initial, len(compressed))
    # A zero output limit must retain the input for subsequent calls.
    assert decoder.decompress(compressed[:offset], 0) == b""
    output = []
    # Bound the calls so a decoder that stops making progress fails the test.
    for _ in range(len(compressed) + len(payload) + 1):
        if decoder.eof:
            break
        chunk = compressed[offset : offset + input_size] if decoder.needs_input else b""
        offset += len(chunk)
        block = decoder.decompress(chunk, output_size)
        assert len(block) <= output_size
        output.append(block)
    assert decoder.eof
    assert b"".join(output) == payload
    assert decoder.unused_data + compressed[offset:] == b"next message"
    assert not decoder.needs_input


@settings(deadline=None)
@given(
    payload=st.binary(max_size=20000),
    input_size=st.sampled_from([1, 7, 127, 8192]),
    output_size=st.sampled_from([1, 37, 8192]),
    wbits=st.sampled_from([-15, 15, 31]),
    dictionary=st.one_of(st.none(), st.binary(max_size=256)),
)
def test_public_decoder_preserves_data_and_trailing_bytes(
    payload, input_size, output_size, wbits, dictionary
):
    if wbits == 31:
        dictionary = None  # Gzip does not support preset dictionaries.
    kwargs = {} if dictionary is None else {"zdict": dictionary}
    encoder = stdlib_zlib.compressobj(wbits=wbits, **kwargs)
    compressed = encoder.compress(payload) + encoder.flush() + b"next message"
    decoder = zlib.decompressobj(wbits, **kwargs)
    output = []
    offset = 0
    pending = b""
    for _ in range(len(compressed) + len(payload) + 1):
        if decoder.eof:
            break
        chunk = compressed[offset : offset + input_size]
        offset += len(chunk)
        block = decoder.decompress(pending + chunk, output_size)
        output.append(block)
        pending = decoder.unconsumed_tail
        assert len(block) <= output_size
    assert decoder.eof
    assert b"".join(output) == payload
    assert decoder.unused_data + compressed[offset:] == b"next message"
    assert not decoder.unconsumed_tail

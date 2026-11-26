import concurrent.futures
import gzip as stdlib_gzip
import io
import threading
import zlib as stdlib_zlib
from zipfile import ZipFile, ZIP_DEFLATED

from hypothesis import given, strategies as st
import pytest

import zlib_rust as zlib
from zlib_rust import gzip


@pytest.mark.parametrize("wbits", [-15, -9, 9, 15, 25, 31])
@pytest.mark.parametrize("level", [0, 1, 6, 9])
def test_formats_interoperate(wbits, level):
    data = bytes(range(256)) * 200
    assert stdlib_zlib.decompress(zlib.compress(data, level, wbits), wbits) == data
    assert zlib.decompress(stdlib_zlib.compress(data, level, wbits), wbits) == data


@pytest.mark.parametrize("module", [zlib, stdlib_zlib])
@pytest.mark.parametrize(
    "wbits,format_wbits", [(0, 9), (0, 15), (16, 31), (32, 9), (32, 15), (32, 31)]
)
def test_decompression_can_infer_window_size(module, wbits, format_wbits):
    payload = b"window size from the stream" * 100
    compressed = stdlib_zlib.compress(payload, wbits=format_wbits)
    assert module.decompress(compressed, wbits) == payload
    decoder = module.decompressobj(wbits)
    assert decoder.decompress(compressed) == payload
    assert decoder.eof


@given(st.binary(max_size=20000), st.integers(min_value=0, max_value=9))
def test_independent_codec_round_trips(data, level):
    assert stdlib_zlib.decompress(zlib.compress(data, level)) == data
    assert zlib.decompress(stdlib_zlib.compress(data, level)) == data


@pytest.mark.parametrize("factory", [bytes, bytearray, memoryview])
def test_contiguous_buffers(factory):
    data = factory(b"immutable or copied input" * 100)
    assert zlib.decompress(zlib.compress(data)) == bytes(data)
    assert zlib.crc32(data) == stdlib_zlib.crc32(data)
    assert zlib.adler32(data) == stdlib_zlib.adler32(data)


class BytesWithOverrides(bytes):
    def __getitem__(self, key):
        raise AssertionError("use the buffer, not Python slicing")

    def __radd__(self, other):
        raise AssertionError("use the buffer, not Python concatenation")

    def __bytes__(self):
        raise AssertionError("use the buffer, not __bytes__")


@pytest.mark.parametrize("module", [zlib, stdlib_zlib])
def test_decoder_reads_the_buffer_of_a_bytes_subclass(module):
    payload = b"buffer contents"
    compressed = BytesWithOverrides(stdlib_zlib.compress(payload) + b"trailer")
    decoder = module.decompressobj()
    first = decoder.decompress(compressed, 3)
    assert first + decoder.decompress(decoder.unconsumed_tail) == payload
    assert decoder.eof
    assert decoder.unused_data == b"trailer"


def test_gzip_decoder_reads_the_buffer_of_a_bytes_subclass():
    payload = b"buffer contents"
    compressed = BytesWithOverrides(stdlib_zlib.compress(payload) + b"trailer")
    decoder = zlib._ZlibDecompressor()
    first = decoder.decompress(compressed, 3)
    assert first + decoder.decompress(b"") == payload
    assert decoder.eof
    assert decoder.unused_data == b"trailer"


@pytest.mark.parametrize(
    "operation", [zlib.compress, zlib.decompress, zlib.crc32, zlib.adler32]
)
def test_noncontiguous_buffer_rejected(operation):
    with pytest.raises(BufferError):
        operation(memoryview(b"abcde")[::2])


@given(st.binary(max_size=10000), st.binary(max_size=10000))
def test_combine_checksums_without_original_bytes(first, second):
    for checksum, combine in [
        (zlib.adler32, zlib.adler32_combine),
        (zlib.crc32, zlib.crc32_combine),
    ]:
        assert combine(checksum(first), checksum(second), len(second)) == checksum(
            first + second
        )


@pytest.mark.parametrize("combine", [zlib.adler32_combine, zlib.crc32_combine])
def test_combine_rejects_negative_lengths(combine):
    with pytest.raises(ValueError):
        combine(1, 1, -1)


def test_bounded_decoder_drains_without_losing_trailing_data():
    data = b"large expansion" * 10000
    decoder = zlib.decompressobj()
    pending = stdlib_zlib.compress(data) + b"next protocol message"
    chunks = []
    while not decoder.eof:
        output = decoder.decompress(pending, max_length=31)
        assert len(output) <= 31
        chunks.append(output)
        pending = decoder.unconsumed_tail
    assert b"".join(chunks) == data
    assert decoder.unused_data == b"next protocol message"


@pytest.mark.parametrize("factory", [gzip.GzipFile, stdlib_gzip.GzipFile])
def test_gzip_reader_handles_concatenated_members_in_bounded_reads(factory):
    data = stdlib_gzip.compress(b"a" * 10000) + stdlib_gzip.compress(b"b" * 10000)
    with factory(fileobj=io.BytesIO(data), mode="rb") as reader:
        chunks = list(iter(lambda: reader.read(37), b""))
    assert max(map(len, chunks)) <= 37
    assert b"".join(chunks) == b"a" * 10000 + b"b" * 10000


def test_gzip_decoder_requests_input_after_sync_flush():
    payload = b"a" * io.DEFAULT_BUFFER_SIZE
    encoder = stdlib_zlib.compressobj(wbits=-15)
    compressed = encoder.compress(payload) + encoder.flush(stdlib_zlib.Z_SYNC_FLUSH)
    decoder = zlib._ZlibDecompressor(wbits=-15)

    assert decoder.decompress(compressed, len(payload)) == payload
    assert decoder.needs_input
    assert not decoder.eof
    assert decoder.decompress(encoder.compress(b"tail") + encoder.flush()) == b"tail"
    assert decoder.eof


def test_gzip_reader_continues_after_sync_flush_at_read_boundary(monkeypatch):
    payload = b"a" * io.DEFAULT_BUFFER_SIZE
    encoder = stdlib_zlib.compressobj(wbits=31)
    prefix = encoder.compress(payload) + encoder.flush(stdlib_zlib.Z_SYNC_FLUSH)
    compressed = prefix + encoder.compress(b"tail") + encoder.flush()
    # Exclude the ten-byte gzip header from the first compressed read.
    monkeypatch.setattr(gzip, "READ_BUFFER_SIZE", len(prefix) - 10)

    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as reader:
        assert reader.read(len(payload)) == payload
        assert reader.read(len(payload)) == b"tail"
        assert reader.read(len(payload)) == b""


def test_gzip_storage_writer_is_readable_by_stdlib():
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as writer:
        for _ in range(100):
            writer.write(b"event data\n")
    assert not stream.closed
    assert stdlib_gzip.decompress(stream.getvalue()) == b"event data\n" * 100


def test_zip_entry_reader_uses_rust_decoder(monkeypatch):
    import zipfile

    data = b"artifact data" * 10000
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("artifact", data)
    original = zipfile._get_decompressor
    monkeypatch.setattr(
        zipfile,
        "_get_decompressor",
        lambda method: (
            zlib.decompressobj(-15) if method == ZIP_DEFLATED else original(method)
        ),
    )
    with ZipFile(buffer) as archive, archive.open("artifact") as entry:
        assert entry.read(41) == data[:41]
        entry.seek(20)
        assert entry.read() == data[20:]


def test_independent_streams_work_concurrently():
    inputs = [bytes([i]) * 100000 for i in range(16)]

    def round_trip(data):
        return zlib.decompress(zlib.compress(data))

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(round_trip, inputs)) == inputs


def test_gzip_decoder_can_be_drained_concurrently():
    payload = b"a" * 1000000
    decoder = zlib._ZlibDecompressor()
    assert decoder.decompress(stdlib_zlib.compress(payload), 0) == b""
    barrier = threading.Barrier(8)

    def drain():
        total = 0
        barrier.wait(timeout=10)
        while True:
            try:
                block = decoder.decompress(b"", 37)
            except EOFError:
                return total
            assert block == b"a" * len(block)
            total += len(block)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(lambda _: drain(), range(8))) == len(payload)


def test_huffman_only_strategy_disables_repeated_string_matching():
    data = b"repeated phrase " * 10000
    regular = zlib.compress(data)
    encoder = zlib.compressobj(strategy=zlib.Z_HUFFMAN_ONLY)
    huffman_only = encoder.compress(data) + encoder.flush()
    assert stdlib_zlib.decompress(huffman_only) == data
    assert len(huffman_only) > len(regular) * 10


@pytest.mark.parametrize("module", [zlib, stdlib_zlib])
@pytest.mark.parametrize("dictionary", [b"", b"preset dictionary"])
def test_gzip_compressor_rejects_explicit_dictionary(module, dictionary):
    with pytest.raises(ValueError):
        module.compressobj(wbits=31, zdict=dictionary)
    encoder = module.compressobj(wbits=31)
    assert stdlib_zlib.decompress(encoder.flush(), wbits=31) == b""


@pytest.mark.parametrize("module", [zlib, stdlib_zlib])
def test_zlib_stream_can_require_an_empty_dictionary(module):
    payload = b"empty preset dictionary"
    # FDICT declares a dictionary with Adler-32 = 1, the empty dictionary.
    header = b"\x78\x20\x00\x00\x00\x01"
    compressed = header + stdlib_zlib.compress(payload, wbits=-15)
    compressed += stdlib_zlib.adler32(payload).to_bytes(4, "big")
    decoder = module.decompressobj(zdict=b"")
    assert decoder.decompress(compressed) == payload
    assert decoder.eof
    with pytest.raises(module.error):
        module.decompressobj().decompress(compressed)


@pytest.mark.parametrize("module", [zlib, stdlib_zlib])
def test_no_flush_is_a_noop_after_finishing_compression(module):
    encoder = module.compressobj()
    payload = b"finished stream"
    compressed = encoder.compress(payload) + encoder.flush()
    assert encoder.flush(module.Z_NO_FLUSH) == b""
    assert stdlib_zlib.decompress(compressed) == payload
    with pytest.raises(module.error):
        encoder.compress(b"more input")


@pytest.mark.parametrize("dictionary", [None, b"wrong dictionary"])
def test_flush_after_dictionary_error_raises(dictionary):
    encoder = stdlib_zlib.compressobj(zdict=b"shared dictionary")
    data = encoder.compress(b"shared dictionary" * 100) + encoder.flush()
    decoder = zlib.decompressobj(
        **({} if dictionary is None else {"zdict": dictionary})
    )
    with pytest.raises(zlib.error):
        decoder.decompress(data)
    with pytest.raises(zlib.error):
        decoder.flush()


@pytest.mark.parametrize("wbits", [15, 31])
@pytest.mark.parametrize("during_flush", [False, True])
def test_decoder_preserves_unconsumed_input_after_trailer_error(wbits, during_flush):
    payload = b"checked stream" * 100
    compressed = stdlib_zlib.compress(payload, wbits=wbits)
    corrupted = compressed[:-1] + bytes([compressed[-1] ^ 1]) + b"next message"
    decoder = zlib.decompressobj(wbits)
    if during_flush:
        assert decoder.decompress(corrupted, 1) == payload[:1]
        with pytest.raises(zlib.error):
            decoder.flush()
    else:
        with pytest.raises(zlib.error):
            decoder.decompress(corrupted)
    assert decoder.unconsumed_tail == b"next message"
    assert decoder.unused_data == b""
    assert not decoder.eof


@pytest.mark.parametrize("module", [zlib, stdlib_zlib])
@pytest.mark.parametrize("wrong_dictionary", [False, True])
def test_dictionary_error_preserves_input_like_cpython(module, wrong_dictionary):
    encoder = stdlib_zlib.compressobj(zdict=b"correct dictionary")
    compressed = encoder.compress(b"correct dictionary" * 100) + encoder.flush()
    compressed += b"next message"
    decoder = module.decompressobj(**({"zdict": b"wrong"} if wrong_dictionary else {}))
    with pytest.raises(module.error):
        decoder.decompress(compressed)
    # CPython saves input for a missing dictionary, but skips that update
    # when installing a supplied dictionary fails.
    assert decoder.unconsumed_tail == (b"" if wrong_dictionary else compressed[6:])


@pytest.mark.parametrize("max_length", [0, 10])
def test_flush_reports_corrupt_checksum(max_length):
    # Follow CPython gh-156173, which fixes silent corruption in flush().
    # Older installed CPython versions still return output instead of raising.
    payload = b"compressed content" * 10000
    data = stdlib_zlib.compress(payload)
    corrupted = data[:-1] + bytes([data[-1] ^ 1])
    decoder = zlib.decompressobj()
    if max_length:
        assert decoder.decompress(corrupted, max_length) == payload[:max_length]
    else:
        with pytest.raises(zlib.error):
            decoder.decompress(corrupted)
    with pytest.raises(zlib.error):
        decoder.flush()


def test_flush_after_invalid_gzip_header_raises():
    decoder = zlib.decompressobj(31)
    with pytest.raises(zlib.error):
        decoder.decompress(b"trailing garbage")
    with pytest.raises(zlib.error):
        decoder.flush()

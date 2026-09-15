import concurrent.futures
import gzip as stdlib_gzip
import io
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


def test_huffman_only_strategy_disables_repeated_string_matching():
    data = b"repeated phrase " * 10000
    regular = zlib.compress(data)
    encoder = zlib.compressobj(strategy=zlib.Z_HUFFMAN_ONLY)
    huffman_only = encoder.compress(data) + encoder.flush()
    assert stdlib_zlib.decompress(huffman_only) == data
    assert len(huffman_only) > len(regular) * 10


def test_wrong_dictionary_remains_an_error_on_flush():
    encoder = stdlib_zlib.compressobj(zdict=b"shared dictionary")
    data = encoder.compress(b"shared dictionary" * 100) + encoder.flush()
    decoder = zlib.decompressobj(zdict=b"wrong dictionary")
    with pytest.raises(zlib.error):
        decoder.decompress(data)
    with pytest.raises(zlib.error):
        decoder.flush()

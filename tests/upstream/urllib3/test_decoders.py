from io import BytesIO
import zlib

import pytest
from urllib3.response import HTTPResponse
from urllib3.exceptions import DecodeError
import urllib3.response as response
import zlib_rust


@pytest.fixture(autouse=True)
def rust_response_decoder(monkeypatch):
    monkeypatch.setattr(response, "zlib", zlib_rust)
    monkeypatch.setattr(HTTPResponse, "DECODER_ERROR_CLASSES",
                        HTTPResponse.DECODER_ERROR_CLASSES + (zlib_rust.error,))


class TestHTTPResponseCodecs:
    def test_decode_deflate(self) -> None:
        data = zlib.compress(b"foo")

        fp = BytesIO(data)
        r = HTTPResponse(fp, headers={"content-encoding": "deflate"})

        assert r.data == b"foo"

    def test_decode_deflate_case_insensitve(self) -> None:
        data = zlib.compress(b"foo")

        fp = BytesIO(data)
        r = HTTPResponse(fp, headers={"content-encoding": "DeFlAtE"})

        assert r.data == b"foo"

    def test_chunked_decoding_deflate(self) -> None:
        data = zlib.compress(b"foo")

        fp = BytesIO(data)
        r = HTTPResponse(
            fp, headers={"content-encoding": "deflate"}, preload_content=False
        )

        assert r.read(1) == b"f"
        assert r.read(2) == b"oo"
        assert r.read() == b""
        assert r.read() == b""

    def test_chunked_decoding_deflate2(self) -> None:
        compress = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
        data = compress.compress(b"foo")
        data += compress.flush()

        fp = BytesIO(data)
        r = HTTPResponse(
            fp, headers={"content-encoding": "deflate"}, preload_content=False
        )

        assert r.read(1) == b"f"
        assert r.read(2) == b"oo"
        assert r.read() == b""
        assert r.read() == b""

    @pytest.mark.parametrize("content_encoding", ["gzip", "x-gzip"])
    def test_chunked_decoding_gzip(self, content_encoding: str) -> None:
        compress = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        data = compress.compress(b"foo")
        data += compress.flush()

        fp = BytesIO(data)
        r = HTTPResponse(
            fp, headers={"content-encoding": content_encoding}, preload_content=False
        )

        assert r.read(1) == b"f"
        assert r.read(2) == b"oo"
        assert r.read() == b""
        assert r.read() == b""

    def test_decode_gzip_multi_member(self) -> None:
        compress = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        data = compress.compress(b"foo")
        data += compress.flush()
        data = data * 3

        fp = BytesIO(data)
        r = HTTPResponse(fp, headers={"content-encoding": "gzip"})

        assert r.data == b"foofoofoo"

    def test_decode_gzip_error(self) -> None:
        fp = BytesIO(b"foo")
        with pytest.raises(DecodeError):
            HTTPResponse(fp, headers={"content-encoding": "gzip"})

    def test_decode_gzip_swallow_garbage(self) -> None:
        # When data comes from multiple calls to read(), data after
        # the first zlib error (here triggered by garbage) should be
        # ignored.
        compress = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        data = compress.compress(b"foo")
        data += compress.flush()
        data = data * 3 + b"foo"

        fp = BytesIO(data)
        r = HTTPResponse(
            fp, headers={"content-encoding": "gzip"}, preload_content=False
        )
        ret = b""
        for _ in range(100):
            ret += r.read(1)
            if r.closed:
                break

        assert ret == b"foofoofoo"

    def test_chunked_decoding_gzip_swallow_garbage(self) -> None:
        compress = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        data = compress.compress(b"foo")
        data += compress.flush()
        data = data * 3 + b"foo"

        fp = BytesIO(data)
        r = HTTPResponse(fp, headers={"content-encoding": "gzip"})

        assert r.data == b"foofoofoo"

    def test_multi_decoding_deflate_deflate(self) -> None:
        data = zlib.compress(zlib.compress(b"foo"))

        fp = BytesIO(data)
        r = HTTPResponse(fp, headers={"content-encoding": "deflate, deflate"})

        assert r.data == b"foo"

    def test_multi_decoding_deflate_gzip(self) -> None:
        compress = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        data = compress.compress(zlib.compress(b"foo"))
        data += compress.flush()

        fp = BytesIO(data)
        r = HTTPResponse(fp, headers={"content-encoding": "deflate, gzip"})

        assert r.data == b"foo"

    def test_multi_decoding_gzip_gzip(self) -> None:
        compress = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        data = compress.compress(b"foo")
        data += compress.flush()

        compress = zlib.compressobj(6, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
        data = compress.compress(data)
        data += compress.flush()

        fp = BytesIO(data)
        r = HTTPResponse(fp, headers={"content-encoding": "gzip, gzip"})

        assert r.data == b"foo"

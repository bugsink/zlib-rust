"""Python's zlib interface, backed by zlib-rs."""

from importlib.metadata import version
from operator import index
from threading import Lock
import sys

from . import _zlib_rust as _native

__version__ = version("zlib-rust")
ZLIB_RS_VERSION = __version__.split(".post")[0]
ZLIB_VERSION = ZLIB_RUNTIME_VERSION = "1.3.1"
error = _native.error

DEFLATED = 8
MAX_WBITS = 15
DEF_MEM_LEVEL = 8
DEF_BUF_SIZE = 16384
Z_NO_COMPRESSION = 0
Z_BEST_SPEED = 1
Z_BEST_COMPRESSION = 9
Z_DEFAULT_COMPRESSION = -1
Z_DEFAULT_STRATEGY = 0
Z_FILTERED = 1
Z_HUFFMAN_ONLY = 2
Z_RLE = 3
Z_FIXED = 4
Z_NO_FLUSH = 0
Z_PARTIAL_FLUSH = 1
Z_SYNC_FLUSH = 2
Z_FULL_FLUSH = 3
Z_FINISH = 4
Z_BLOCK = 5
Z_TREES = 6


def _as_bytes(data):
    if isinstance(data, bytes):
        return data
    view = memoryview(data)
    if not view.c_contiguous:
        raise BufferError("memoryview: underlying buffer is not C-contiguous")
    return view.tobytes()


def _c_int(value):
    value = index(value)
    if not -(1 << 31) <= value < (1 << 31):
        raise OverflowError("Python int too large to convert to C int")
    return value


def _length(value):
    value = index(value)
    if not -sys.maxsize - 1 <= value <= sys.maxsize:
        raise OverflowError("Python int too large to convert to C ssize_t")
    return value


def adler32(data, value=1, /):
    return _native.adler32(_as_bytes(data), index(value) & 0xffffffff)


def crc32(data, value=0, /):
    return _native.crc32(_as_bytes(data), index(value) & 0xffffffff)


def adler32_combine(adler1, adler2, len2, /):
    length = _length(len2)
    if length < 0:
        raise ValueError("len2 must be non-negative")
    return _native.adler32_combine(index(adler1) & 0xffffffff, index(adler2) & 0xffffffff, length)


def crc32_combine(crc1, crc2, len2, /):
    return _native.crc32_combine(index(crc1) & 0xffffffff, index(crc2) & 0xffffffff, _length(len2))


class _Compress:
    def __new__(cls):
        raise TypeError("cannot create 'zlib_rust._Compress' instances")

    def __init__(self, level, wbits, dictionary):
        self._inner = _native.Encoder(level, wbits, dictionary)
        self._finished = False
        self._lock = Lock()

    def compress(self, data, /):
        data = _as_bytes(data)
        with self._lock:
            if self._finished:
                raise error("Error -2 while compressing data: inconsistent stream state")
            return self._inner.process(data, Z_NO_FLUSH)

    def flush(self, mode=Z_FINISH, /):
        mode = _c_int(mode)
        with self._lock:
            if self._finished:
                raise error("Error -2 while flushing: inconsistent stream state")
            if mode not in range(6):
                raise error("Error -2 while flushing: invalid flush mode")
            if mode == Z_NO_FLUSH:
                return b""
            result = self._inner.process(b"", mode)
            if mode == Z_FINISH:
                self._finished = True
            return result

    def copy(self):
        with self._lock:
            if self._finished:
                raise ValueError("Inconsistent stream state")
            raise NotImplementedError("zlib-rs does not expose safe stream copying")

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        return self.copy()


class _Decompress:
    def __new__(cls):
        raise TypeError("cannot create 'zlib_rust._Decompress' instances")

    def __init__(self, wbits, dictionary):
        self._inner = _native.Decoder(wbits, dictionary)
        self._eof = False
        self._unused_data = b""
        self._unconsumed_tail = b""
        self._closed = False
        self._lock = Lock()

    @property
    def eof(self):
        return self._eof

    @property
    def unused_data(self):
        return self._unused_data

    @property
    def unconsumed_tail(self):
        return self._unconsumed_tail

    def _decompress(self, data, max_length):
        if self._closed:
            raise error("Error -2 while decompressing data: inconsistent stream state")
        if self._eof:
            self._unused_data += data
            return b""
        output, consumed, self._eof = self._inner.process(data, max_length)
        remainder = data[consumed:]
        if self._eof:
            self._unused_data += remainder
            self._unconsumed_tail = b""
        else:
            self._unconsumed_tail = remainder
        return output

    def decompress(self, data, /, max_length=0):
        data = _as_bytes(data)
        max_length = _length(max_length)
        if max_length < 0:
            raise ValueError("max_length must be non-negative")
        with self._lock:
            return self._decompress(data, max_length)

    def flush(self, length=DEF_BUF_SIZE, /):
        length = _length(length)
        if length <= 0:
            raise ValueError("length must be greater than zero")
        with self._lock:
            if self._closed:
                return b""
            result = self._decompress(self._unconsumed_tail, 0)
            if self._eof:
                self._closed = True
            return result

    def copy(self):
        with self._lock:
            if self._closed:
                raise ValueError("Inconsistent stream state")
            raise NotImplementedError("zlib-rs does not expose safe stream copying")

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        return self.copy()


def compressobj(level=Z_DEFAULT_COMPRESSION, method=DEFLATED, wbits=MAX_WBITS,
                memLevel=DEF_MEM_LEVEL, strategy=Z_DEFAULT_STRATEGY, zdict=b""):
    level, method, wbits, memLevel, strategy = map(_c_int, (level, method, wbits, memLevel, strategy))
    if not (-1 <= level <= 9 and method == DEFLATED and 1 <= memLevel <= 9 and 0 <= strategy <= 4):
        raise ValueError("Invalid initialization option")
    if not (-15 <= wbits <= -9 or 8 <= wbits <= 15 or 25 <= wbits <= 31):
        raise ValueError("Invalid initialization option")
    if memLevel != DEF_MEM_LEVEL or strategy != Z_DEFAULT_STRATEGY:
        raise NotImplementedError("zlib-rs does not expose safe compression configuration")
    result = object.__new__(_Compress)
    result.__init__(level, 9 if wbits == 8 else wbits, _as_bytes(zdict))
    return result


def decompressobj(wbits=MAX_WBITS, zdict=b""):
    wbits = _c_int(wbits)
    if not (wbits == 0 or -15 <= wbits <= -8 or 8 <= wbits <= 15 or 24 <= wbits <= 31 or 40 <= wbits <= 47):
        raise ValueError("Invalid initialization option")
    result = object.__new__(_Decompress)
    result.__init__(wbits, _as_bytes(zdict))
    return result


def compress(data, /, level=Z_DEFAULT_COMPRESSION, wbits=MAX_WBITS):
    data = _as_bytes(data)
    try:
        encoder = compressobj(level=level, wbits=wbits)
    except ValueError as exc:
        raise error("Error -2 while compressing data: invalid initialization option") from exc
    return encoder.compress(data) + encoder.flush()


def decompress(data, /, wbits=MAX_WBITS, bufsize=DEF_BUF_SIZE):
    data = _as_bytes(data)
    if _length(bufsize) < 0:
        raise ValueError("bufsize must be non-negative")
    try:
        decoder = decompressobj(wbits)
    except ValueError as exc:
        raise error("Error -2 while preparing to decompress data: invalid initialization option") from exc
    output = decoder.decompress(data)
    if not decoder.eof:
        raise error("Error -5 while decompressing data: incomplete or truncated stream")
    return output


class _ZlibDecompressor:
    """Retain unconsumed input for CPython's gzip file reader."""

    def __init__(self, wbits=MAX_WBITS, zdict=b""):
        self._decoder = decompressobj(wbits, zdict)
        self._pending = b""
        self.needs_input = True

    @property
    def eof(self):
        return self._decoder.eof

    @property
    def unused_data(self):
        return self._decoder.unused_data

    def decompress(self, data, max_length=-1):
        if self.eof:
            raise EOFError("End of stream already reached")
        data = _as_bytes(data)
        max_length = _length(max_length)
        self._pending += data
        if max_length == 0:
            self.needs_input = not self._pending
            return b""
        result = self._decoder.decompress(self._pending, max(0, max_length))
        self._pending = self._decoder.unconsumed_tail
        self.needs_input = not self._pending and (max_length < 0 or len(result) < max_length)
        if self.eof:
            self.needs_input = False
        return result

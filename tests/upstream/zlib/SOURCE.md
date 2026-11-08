# zlib inflate edge cases

Source: zlib commit `99623ef7097352da7993ba614161fd6a311e046e`,
[`test/infcover.c`](https://github.com/madler/zlib/blob/99623ef7097352da7993ba614161fd6a311e046e/test/infcover.c).
The upstream zlib license is copied unchanged as `LICENSE`.

`test_infcover.py` is a Python adaptation, not an unchanged copy. It includes
all 42 `inf()` and `try()` input vectors from `cover_wrap`, `cover_inflate`,
and `cover_fast`: 26 error cases and 16 successful decoding cases. Input bytes,
case descriptions, and window sizes are retained. Upstream's hexadecimal
notation permits single-digit bytes; these are zero-padded when represented
with Python's `bytes.fromhex()`.

Adaptations to the public Python interface:

- `Z_DATA_ERROR` and `Z_NEED_DICT` become `zlib_rust.error`. The error messages
  asserted by upstream's `try()` helper are retained. Its `inf()` helper only
  asserts error codes, so those cases do not acquire message assertions.
  Each error vector is run both in one call and with one-byte input chunks.
- Successful cases retain the input step and output-buffer size passed to
  `inf()`. A zero output-buffer size becomes a one-byte limit: Python's
  `max_length=0` means unlimited output, not a buffer of zero bytes. The `try()`
  vectors use a 257-byte output limit to exercise repeated calls.
- Python exposes `eof` rather than C return codes. The two header/prefix-only
  successful inputs (`set window size from header`, `compute adler32`) must
  leave `eof` false; the remaining successful inputs must finish after draining
  bounded output. We do not equate an intermediate `Z_OK` with a final EOF.
- Successful decoded bytes are compared with the independent standard-library
  decoder, adding an output check to upstream's status-based harness. We also
  assert the output limit and forward progress while resubmitting unconsumed
  input.

The C harness additionally exercises `inflateBack`, `Z_TREES`, custom allocators,
header retrieval, stream copying/reset, and deliberate internal state changes.
Those operations are not exposed by our public Python API and are not ported.
The `cover_fast` vectors remain useful input cases, but the Python tests make
no claim to select the same internal fast path as the C implementation.

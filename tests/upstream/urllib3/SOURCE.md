# urllib3

Source: urllib3 2.5.0, commit `aaab4eccc10c965897540b21e15f11859d0b62e7`:
<https://github.com/urllib3/urllib3/blob/aaab4eccc10c965897540b21e15f11859d0b62e7/test/test_response.py>.
The MIT license is included as `LICENSE.txt`.

Twelve HTTP response decoder tests were selected from `test/test_response.py`.
Their bodies and assertions are unchanged. They cover zlib and raw DEFLATE,
gzip aliases, small incremental reads, concatenated members, malformed input,
trailing garbage, and layered content encodings.

The added fixture substitutes zlib-rust in urllib3's response module and adds
its exception to the HTTP response decoder's exception tuple. The fixture is
scoped to each test and restored afterwards. This is test integration, not a
production monkeypatch shipped by the package. Input streams are still produced
by the independent standard-library zlib encoder.

The consumer dependency is pinned in the test extra. Updating that dependency
does not change the provenance of these copied test bodies.

"""
Plug-and-play streaming sink for full MARCXML records.

Writes records one at a time to rotating gzipped shard files, so memory use
stays constant no matter how many records are saved. Each worker process should
create its own sink (no shared state, no locking); shard names are prefixed
with a unique tag to avoid collisions.

Usage inside a worker:

    from record_sink import RecordSink

    with RecordSink("k10plus/data/filtered", tag=f"{Path(file_path).stem}_{start}") as sink:
        for event, elem in etree.iterparse(...):
            ...
            if keep:
                sink.write(elem)   # call BEFORE elem.clear()
            elem.clear()

Output: <out_dir>/<tag>_00000.xml.gz, <tag>_00001.xml.gz, ... each a valid
<collection> of <record> elements (self-contained, namespace-declared).
"""

import gzip
from pathlib import Path

from lxml import etree

MARC_NS = "http://www.loc.gov/MARC21/slim"
_HEADER = f'<?xml version="1.0" encoding="UTF-8"?>\n<collection xmlns="{MARC_NS}">\n'.encode()
_FOOTER = b"</collection>\n"


class RecordSink:
    def __init__(
        self,
        out_dir: str | Path,
        tag: str,
        max_records_per_file: int = 100_000,
        compresslevel: int = 3,
    ):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.tag = tag
        self.max_records = max_records_per_file
        self.compresslevel = compresslevel
        self.shard_idx = 0
        self.in_shard = 0
        self.total = 0
        self._f = None

    def _open_shard(self):
        path = self.out_dir / f"{self.tag}_{self.shard_idx:05d}.xml.gz"
        self._f = gzip.open(path, "wb", compresslevel=self.compresslevel)
        self._f.write(_HEADER)
        self.in_shard = 0

    def _close_shard(self):
        if self._f is not None:
            self._f.write(_FOOTER)
            self._f.close()
            self._f = None
            self.shard_idx += 1

    def write(self, elem) -> None:
        """Serialize one <record> element straight to disk (nothing is retained)."""
        if self._f is None:
            self._open_shard()
        # with_tail=False: drop whitespace between records in the source file
        self._f.write(etree.tostring(elem, encoding="utf-8", with_tail=False))
        self._f.write(b"\n")
        self.in_shard += 1
        self.total += 1
        if self.in_shard >= self.max_records:
            self._close_shard()

    def close(self) -> int:
        self._close_shard()
        return self.total

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

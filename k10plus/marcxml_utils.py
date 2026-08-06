"""
Shared utilities for streaming concatenated MARCXML dump files.

K10Plus dumps may consist of multiple adjacent XML documents of the form:

    <?xml version="1.0" encoding="UTF-8"?>
    <marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim">
      ...records...
    </marc:collection><?xml version="1.0" encoding="UTF-8"?>
    <marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim">
      ...more records...
    </marc:collection>

Use FilteredXMLStream to present such a file to pymarc.map_xml as a single
well-formed XML document.
"""

import io

# The exact byte sequence that separates two concatenated MARCXML documents in
# a K10Plus dump.  The sequence is replaced with an equal number of spaces so
# the overall byte length is preserved and any downstream SAX/expat parser sees
# a single <marc:collection> root element.
#
# If future dumps use a different encoding declaration or omit the newline,
# add the alternative seam pattern here and extend _SEAM_TARGETS accordingly.
_SEAM_TARGETS: list[bytes] = [
    # Standard K10Plus dump seam (UTF-8, newline between ?> and <marc:)
    b'</marc:collection><?xml version="1.0" encoding="UTF-8"?>\n'
    b'<marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim">',
    # Alternative: no newline between ?> and <marc:collection>
    b'</marc:collection><?xml version="1.0" encoding="UTF-8"?>'
    b'<marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim">',
]


class FilteredXMLStream(io.RawIOBase):
    """
    Streaming wrapper that merges concatenated MARCXML documents into a single
    well-formed document, suitable for ``pymarc.map_xml``.

    Each document-boundary seam is replaced in-place with an equal number of
    space bytes so the stream length is preserved.  The replacement is applied
    as data flows through so memory usage stays proportional to the read
    buffer, not the file size.

    Example usage::

        with open("kxp.mrcxml", "rb") as f:
            pymarc.map_xml(callback, FilteredXMLStream(f))
    """

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self._buf = bytearray()
        # Pre-compute replacements (same length as each target)
        self._seams: list[tuple[bytes, bytes]] = [
            (t, b" " * len(t)) for t in _SEAM_TARGETS
        ]
        # Lookahead: keep at least this many bytes in the buffer so that a
        # seam straddling a chunk boundary is always seen in its entirety.
        self._lookahead = max(len(t) for t in _SEAM_TARGETS)

    def readable(self):
        return True

    def read(self, size=-1):
        if size is None or size < 0:
            size = 65536

        # Pull enough data to guarantee we see any seam that may span a chunk
        # boundary before we emit the next `size` bytes.
        if len(self._buf) < size + self._lookahead:
            chunk = self.fileobj.read(size + self._lookahead)
            if chunk:
                self._buf.extend(chunk)

        # Replace all known seam patterns in the current buffer
        for target, replacement in self._seams:
            pos = self._buf.find(target)
            while pos != -1:
                self._buf[pos : pos + len(target)] = replacement
                pos = self._buf.find(target, pos + len(replacement))

        is_eof = len(self._buf) < size + self._lookahead
        bytes_to_read = len(self._buf) if is_eof else size

        result = bytes(self._buf[:bytes_to_read])
        del self._buf[:bytes_to_read]
        return result

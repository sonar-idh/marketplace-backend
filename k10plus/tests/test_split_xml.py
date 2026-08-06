import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from k10plus.split_xml import split_dump


def test_split_dump_basic():
    # Create a dummy MARC XML collection with 5 records
    marc_template = """<?xml version="1.0" encoding="UTF-8"?>
<marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim">
  <marc:record>
    <marc:controlfield tag="001">rec1</marc:controlfield>
  </marc:record>
  <marc:record>
    <marc:controlfield tag="001">rec2</marc:controlfield>
  </marc:record>
  <marc:record>
    <marc:controlfield tag="001">rec3</marc:controlfield>
  </marc:record>
  <marc:record>
    <marc:controlfield tag="001">rec4</marc:controlfield>
  </marc:record>
  <marc:record>
    <marc:controlfield tag="001">rec5</marc:controlfield>
  </marc:record>
</marc:collection>
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_input = Path(tmpdir) / "input.xml"
        tmp_output_dir = Path(tmpdir) / "chunks"

        with open(tmp_input, "w", encoding="utf-8") as f:
            f.write(marc_template)

        # Split with 2 records per file
        split_dump(tmp_input, tmp_output_dir, records_per_file=2)

        # We expect:
        # kxp_chunk_001.xml -> 2 records (rec1, rec2)
        # kxp_chunk_002.xml -> 2 records (rec3, rec4)
        # kxp_chunk_003.xml -> 1 record (rec5)

        chunk_files = sorted(os.listdir(tmp_output_dir))
        assert len(chunk_files) == 3

        # Verify chunk 1
        chunk1_path = tmp_output_dir / chunk_files[0]
        tree1 = ET.parse(chunk1_path)
        root1 = tree1.getroot()
        assert root1.tag == "{http://www.loc.gov/MARC21/slim}collection"
        records1 = root1.findall("{http://www.loc.gov/MARC21/slim}record")
        assert len(records1) == 2
        assert (
            records1[0].find("{http://www.loc.gov/MARC21/slim}controlfield").text
            == "rec1"
        )
        assert (
            records1[1].find("{http://www.loc.gov/MARC21/slim}controlfield").text
            == "rec2"
        )

        # Verify chunk 2
        chunk2_path = tmp_output_dir / chunk_files[1]
        tree2 = ET.parse(chunk2_path)
        root2 = tree2.getroot()
        records2 = root2.findall("{http://www.loc.gov/MARC21/slim}record")
        assert len(records2) == 2
        assert (
            records2[0].find("{http://www.loc.gov/MARC21/slim}controlfield").text
            == "rec3"
        )
        assert (
            records2[1].find("{http://www.loc.gov/MARC21/slim}controlfield").text
            == "rec4"
        )

        # Verify chunk 3
        chunk3_path = tmp_output_dir / chunk_files[2]
        tree3 = ET.parse(chunk3_path)
        root3 = tree3.getroot()
        records3 = root3.findall("{http://www.loc.gov/MARC21/slim}record")
        assert len(records3) == 1
        assert (
            records3[0].find("{http://www.loc.gov/MARC21/slim}controlfield").text
            == "rec5"
        )

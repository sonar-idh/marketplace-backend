import subprocess
from pathlib import Path
import pytest
import rdflib

HERE = Path(__file__).parent
STYLESHEET = HERE.parent / "ead2rico_main.xsl"
TEST_XML_PATH = HERE.parent / "ead_DE-1_5364_test.xml"

# Saxon-HE (XSLT 3.0) statt saxonb-xslt (Saxon-B, nur XSLT 2.0) - das Stylesheet
# nutzt XSLT-3.0/XPath-3.1-Funktionen (unparsed-text-lines, map:*), die Saxon-B nicht kennt.
SAXON_HE_JAR = Path("/usr/share/java/Saxon-HE.jar")


def run_transform(**params) -> str:
    args = [
        "java", "-cp", str(SAXON_HE_JAR), "net.sf.saxon.Transform",
        f"-s:{TEST_XML_PATH}", f"-xsl:{STYLESHEET}",
    ]
    args += [f"{k}={v}" for k, v in params.items()]
    result = subprocess.run(args, capture_output=True, text=True, cwd=STYLESHEET.parent)
    if result.returncode != 0:
        pytest.fail(f"Saxon failed:\n{result.stderr}")
    return result.stdout


def test_transform_produces_valid_turtle():
    ttl = run_transform()
    g = rdflib.Graph()
    try:
        g.parse(data=ttl, format="turtle")
    except Exception as e:
        pytest.fail(f"Output is not valid Turtle: {e}\n")

    assert len(g) > 0, "Parsed graph is empty"

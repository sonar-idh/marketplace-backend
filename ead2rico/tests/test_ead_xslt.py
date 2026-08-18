import subprocess
from pathlib import Path
import pytest
import rdflib
from rdflib import RDF, Literal, Namespace, XSD

HERE = Path(__file__).parent
STYLESHEET = HERE.parent / "ead2rico_main.xsl"
TEST_XML_PATH = HERE.parent / "ead_DE-1_5364_test.xml"
SNIPPET_XML_PATH = HERE / "ead_test_snippet.xml"
SAXON_HE_JAR = Path("/usr/share/java/Saxon-HE.jar")

RICO = Namespace("https://www.ica.org/standards/RiC/ontology#")
KPE = Namespace("https://kalliope-verbund.info/ead?ead.id=")
GND = Namespace("https://d-nb.info/gnd/")
ISIL = Namespace("https://isil.staatsbibliothek-berlin.de/isil/")

TEST_BESTAND = KPE["DE-611-BF-5364"]
tricky_title = 'Brief mit "Anführungszeichen" und \\Backslash\\'


def run_transform(source=TEST_XML_PATH, **params) -> str:
    """Führt die Saxon-Transformation für die EAD-Testdatein aus."""
    args = [
        "java",
        "-cp",
        str(SAXON_HE_JAR),
        "net.sf.saxon.Transform",
        f"-s:{source}",
        f"-xsl:{STYLESHEET}",
    ]
    args += [f"{k}={v}" for k, v in params.items()]
    result = subprocess.run(args, capture_output=True, text=True, cwd=STYLESHEET.parent)
    if result.returncode != 0:
        pytest.fail(f"Saxon failed:\n{result.stderr}")
    return result.stdout


def parse_turtle(ttl: str) -> rdflib.Graph:
    g = rdflib.Graph()
    try:
        g.parse(data=ttl, format="turtle")
    except Exception as e:
        pytest.fail(f"Output is not valid Turtle: {e}\n{ttl}")
    return g


@pytest.fixture(scope="module")
def transform_snippet() -> rdflib.Graph:
    """Einmaliger Saxon-Lauf über die statische Snippet-Datei (ead_test_snippet.xml),
    um gezielt Einzelfälle wie fehlende genreform='Brief' oder Escaping abzudecken."""
    return parse_turtle(run_transform(source=SNIPPET_XML_PATH))


@pytest.fixture(scope="module")
def graph() -> rdflib.Graph:
    """Einmaliger Saxon-Lauf über den realen Testdatensatz, von allen
    inhaltlichen Tests in dieser Datei wiederverwendet."""
    return parse_turtle(run_transform())


# ============ Grundlegende Validität ============


def test_transform_produces_valid_turtle(graph):
    assert len(graph) > 0, "Parsed graph is empty"


# ============ Bestand (RecordSet) ============


def test_archdesc_becomes_recordset(graph):
    # Transformation erfasst den URI des Testbestands als rico:RecordSet
    assert (TEST_BESTAND, RDF.type, RICO.RecordSet) in graph


def test_recordset_title(graph):
    # Transformation erfasst den Titel des Testbestands als rico:title
    assert graph.value(TEST_BESTAND, RICO.title) == Literal(
        "N.Mus.Nachl. 15 (Teilnachlass Arnold Schönberg)"
    )


def test_recordset_identifier(graph):
    # Transformation erfasst die KPE-ID des Testbestands als rico:identifier
    assert graph.value(TEST_BESTAND, RICO.identifier) == Literal("DE-611-BF-5364")


def test_recordset_type_from_gnd_genreform(graph):
    # Transformation erhaelt den GND-referenzierten Dokumententyp des Testbestands (Teilnachlass)
    assert (TEST_BESTAND, RICO.hasRecordSetType, GND["4123811-4"]) in graph


def test_recordset_holder_from_isil_repository(graph):
    # Transformation erhaelt den ISIL-referenzierten Aufbewahrungsort des Testbestands
    assert (TEST_BESTAND, RICO.hasOrHadHolder, ISIL["DE-1"]) in graph


def test_recordset_organic_provenance_lists_both_bestandsbildner(graph):
    # Transformation erhaelt die beiden GND-referenzierten Bestandsbildner des Testbestands
    provenance = set(graph.objects(TEST_BESTAND, RICO.hasOrganicProvenance))
    assert provenance == {GND["118610023"], GND["116701218"]}


def test_recordset_includes_transitive_matches_brief_count(graph):
    # Transformation erhaelt die 39 <c> mit genreform='Brief' des Testbestands
    included = set(graph.objects(TEST_BESTAND, RICO.includesTransitive))
    assert len(included) == 39


# ============ Verzeichnungseinheiten (Record) ============


def test_record_count_matches_brief_count(graph):
    # Alle 39 <c> mit genreform='Brief' des Testbestands werden als rico:Record erfasst
    records = set(graph.subjects(RDF.type, RICO.Record))
    assert len(records) == 39


def test_record_is_or_was_included_in_bestand(graph):
    # Test-Record referenziert den korrekten Bestand
    record = KPE["DE-611-HS-3695945"]
    assert (record, RICO.isOrWasIncludedIn, TEST_BESTAND) in graph


def test_record_author_and_addressee(graph):
    # Verfasser und Adressat des Test-Records werden erfasst
    record = KPE["DE-611-HS-3695945"]  # Brief Schönberg -> Alban Berg
    assert (record, RICO.hasAuthor, GND["118610023"]) in graph
    assert (record, RICO.hasAddressee, GND["118509322"]) in graph


def test_record_addressee_without_gnd_reference_is_omitted(graph):
    # Adressat ohne GND-Referenz wird nicht erfasst
    record = KPE[
        "DE-611-HS-3685983"
    ]  # Adressat "Unbekannt" hat source='KPE', keine GND-authfilenumber
    assert graph.value(record, RICO.hasAddressee) is None


def test_record_date_day_precision(graph):
    # Datumsangabe mit Tagespraezision wird korrekt erfasst
    record = KPE["DE-611-HS-3695945"]  # normal="19300809"
    assert graph.value(record, RICO.beginningDate) == Literal(
        "1930-08-09", datatype=XSD.date
    )
    assert graph.value(record, RICO.endDate) == Literal("1930-08-09", datatype=XSD.date)


def test_record_date_month_precision_resolves_to_full_month(graph):
    # Datumsangabe mit Monatspraezision wird korrekt erfasst
    record = KPE["DE-611-HS-3685983"]  # normal="1934-11"
    assert graph.value(record, RICO.beginningDate) == Literal(
        "1934-11-01", datatype=XSD.date
    )
    assert graph.value(record, RICO.endDate) == Literal("1934-11-30", datatype=XSD.date)


def test_dates_are_always_typed_as_xs_date(graph):
    # rico:beginningDate/endDate sollen unabhaengig von der erkannten Praezision immer xs:date sein, nie xs:gYear/xs:gYearMonth.
    for _, _, o in graph.triples((None, RICO.beginningDate, None)):
        assert o.datatype == XSD.date
    for _, _, o in graph.triples((None, RICO.endDate, None)):
        assert o.datatype == XSD.date


# ============ Tests auf Grundlage von EAD-Snippets (ead_test_snippet.xml) ============


def test_c_without_brief_genreform_produces_no_record(transform_snippet):
    # <c>-Element ohne genreform 'Brief' erzeugt keinen Record
    assert (KPE["TEST-C-NOBRIEF"], RDF.type, RICO.Record) not in transform_snippet


def test_title_escaping_roundtrips_through_turtle(transform_snippet):
    # Literale mit Anfuehrungszeichen oder Backslashes werden korrekt geschrieben
    assert transform_snippet.value(KPE["TEST-C-ESCAPE"], RICO.title) == Literal(
        tricky_title
    )


def test_date_year_precision(transform_snippet):
    # Datumsangabe mit Jahrespraezision wird korrekt erfasst
    record = KPE["TEST-C-DATE-YEAR"]
    assert transform_snippet.value(record, RICO.beginningDate) == Literal(
        "1934-01-01", datatype=XSD.date
    )
    assert transform_snippet.value(record, RICO.endDate) == Literal(
        "1934-12-31", datatype=XSD.date
    )


def test_date_range(transform_snippet):
    # Datumsangabe mit Zeitspanne wird korrekt erfasst
    record = KPE["TEST-C-DATE-RANGE"]
    assert transform_snippet.value(record, RICO.beginningDate) == Literal(
        "1930-01-01", datatype=XSD.date
    )
    assert transform_snippet.value(record, RICO.endDate) == Literal(
        "1931-12-31", datatype=XSD.date
    )


def test_date_range_with_swapped_bounds_still_resolves_to_min_max(transform_snippet):
    # Datumsangabe mit vertauschter Zeitspanne wird korrekt erfasst
    record = KPE["TEST-C-DATE-RANGE-SWAPPED"]
    assert transform_snippet.value(record, RICO.beginningDate) == Literal(
        "1930-01-01", datatype=XSD.date
    )
    assert transform_snippet.value(record, RICO.endDate) == Literal(
        "1931-12-31", datatype=XSD.date
    )


def test_date_invalid_day_is_repaired_to_month_precision(transform_snippet):
    # Kalendarisch nicht existierendes Datum wird auf Monatsgrenzen zurueckgefuehrt statt verworfen.
    record = KPE["TEST-C-DATE-INVALID-DAY"]
    assert transform_snippet.value(record, RICO.beginningDate) == Literal(
        "2013-02-01", datatype=XSD.date
    )
    assert transform_snippet.value(record, RICO.endDate) == Literal(
        "2013-02-28", datatype=XSD.date
    )


def test_date_missing_normal_attribute_produces_no_date_triples(transform_snippet):
    # Datum ohne normal-Attribut wird nicht erfasst
    record = KPE["TEST-C-DATE-MISSING-NORMAL"]
    assert transform_snippet.value(record, RICO.beginningDate) is None
    assert transform_snippet.value(record, RICO.endDate) is None


def test_date_unparseable_normal_produces_no_date_triples(transform_snippet):
    # Ungueltiges Datumsformat wird nicht erfasst
    record = KPE["TEST-C-DATE-UNPARSEABLE"]
    assert transform_snippet.value(record, RICO.beginningDate) is None
    assert transform_snippet.value(record, RICO.endDate) is None

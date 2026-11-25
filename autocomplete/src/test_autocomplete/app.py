from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx
from typing import Annotated, Literal
from fastapi import Query
import html
import unicodedata

app = FastAPI()

Mode = Literal["gnd", "kpe"]

def get_query(search_term: str, mode: Mode) -> str:
    term = search_term.strip()
    if mode == "gnd":
        return f"""
        PREFIX gndo: <https://d-nb.info/standards/elementset/gnd#>
        PREFIX ql: <http://qlever.cs.uni-freiburg.de/builtin-functions/>

        SELECT DISTINCT ?s ?label ?dateOfBirth ?dateOfDeath WHERE {{
            ?t ql:contains-word "{term}*" .
            ?t ql:contains-entity ?label .
            ?s gndo:preferredNameForThePerson|gndo:preferredNameForTheCorporateBody ?label .
            OPTIONAL {{ ?s gndo:dateOfBirth ?dateOfBirth . }}
            OPTIONAL {{ ?s gndo:dateOfDeath ?dateOfDeath . }}
        }}
        ORDER BY ?label
        LIMIT 50
        """
    lc = term.lower()
    return f"""
    PREFIX gndo: <https://d-nb.info/standards/elementset/gnd#>
    PREFIX ql: <http://qlever.cs.uni-freiburg.de/builtin-functions/>

    SELECT DISTINCT ?s ?label ?dateOfBirth ?dateOfDeath WHERE {{
      ?t ql:contains-word "{term}*" .
      ?t ql:contains-entity ?label .
      ?s gndo:preferredNameForThePerson|gndo:preferredNameForTheCorporateBody ?label .
      {{
        SELECT DISTINCT ?s WHERE {{
          {{ ?s <info:hasCorrespondent> [] }}
          UNION
          {{ [] <info:hasCorrespondent> ?s }}
        }}
      }}
      OPTIONAL {{ ?s gndo:dateOfBirth ?dateOfBirth . }}
      OPTIONAL {{ ?s gndo:dateOfDeath ?dateOfDeath . }}
    }}
    ORDER BY ?label
    LIMIT 50
    """
    


def fetch_qlever(search_term: str, mode: Mode) -> tuple[list, float]:
    query = get_query(search_term, mode)
    r = httpx.get(
        "http://localhost:7019",
        params={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=60,
    )
    if r.is_error:
        print(r.text)
    r.raise_for_status()
    ms = r.elapsed.total_seconds() * 1000
    bindings = r.json()["results"]["bindings"]
    results = []
    for row in bindings:
        results.append(
            {
                "entity": row["s"]["value"],
                "label": row["label"]["value"],
                "dateOfBirth": str(row["dateOfBirth"]["value"])
                if "dateOfBirth" in row
                else None,
                "dateOfDeath": str(row["dateOfDeath"]["value"])
                if "dateOfDeath" in row
                else None,
            }
        )
        print(row["s"]["value"], row["label"]["value"])
    return results, ms


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!doctype html>
    <html lang="de">
        <head>
    <meta charset="UTF-8" />
    <title>Qlever Autocomplete</title>
    <script src="https://unpkg.com/htmx.org@2"></script>
</head>
<body>
    <h1>Qlever Autocomplete</h1>

    <input type="hidden" id="mode" name="mode" value="gnd" />
    <button type="button" id="mode-btn" onclick="toggleMode()">GND</button>

    <label for="site-search">Search the site:</label>
    <input type="search" id="site-search" name="q" autocomplete="off"
           hx-get="/suggest"
           hx-trigger="input changed delay:200ms, modechange"
           hx-include="#mode"
           hx-sync="this:replace"
           hx-target="#results" />
    <div id="results"></div>

    <script>
      const LABELS = { gnd: "GND", kpe: "KPE + GND" };

      function toggleMode() {
        const m = document.getElementById("mode");
        m.value = m.value === "gnd" ? "kpe" : "gnd";
        document.getElementById("mode-btn").textContent = LABELS[m.value];
        htmx.trigger("#site-search", "modechange");
      }
    </script>
</body>
    </html>
    """


def render_item(res):
    text = unicodedata.normalize("NFC", res["label"])
    if res.get("dateOfBirth"):
        text += f" {res['dateOfBirth']}"
    if res.get("dateOfDeath"):
        text += f" - {res['dateOfDeath']}"
    return f"<li>{html.escape(text)}</li>"


@app.get("/suggest", response_class=HTMLResponse)
def get_completion(
    q: Annotated[
        str,
        Query(max_length=40, pattern=r"^(?:[^\W\d_](?:[^\W\d_]|[ \-,])*)?$"),
    ] = "",
    mode: Mode = "gnd",
):
    if len(q.strip()) < 3:
        return ""
    results, ms = fetch_qlever(q, mode)
    timing = f"<p><small>{len(results)} Treffer in {ms:.0f} ms</small></p>"
    if not results:
        return timing + "<p>Keine Treffer</p>"
    items = "".join(render_item(res) for res in results)
    return f"{timing}<ul>{items}</ul>"

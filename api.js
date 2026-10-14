import http from "node:http";

const PORT = 3000;
const SPARQL_ENDPOINT = `${process.env.SPARQL_ENDPOINT}`;

const PARAMS = {
  source: "source",
  source_label: "sourceLabels",
  target: "target",
  target_label: "targetLabels",
  relation: "relation",
  relation_direction: "relationDirection",
  reference: "reference",
  reference_date: "referenceDate",
};

function escapeSparqlString(value) {
  return value
    .replaceAll("\\", "\\\\")
    .replaceAll('"', '\\"')
    .replaceAll("\n", "\\n")
    .replaceAll("\r", "\\r");
}

function buildQuery(searchParams) {
  const filters = [];

  for (const [parameter, variable] of Object.entries(PARAMS)) {
    const value = searchParams.get(parameter);

    if (value) {
      filters.push(
        `FILTER REGEX(STR(?${variable}), "${escapeSparqlString(value)}", "i") .`
      );
    }
  }

  return `
    SELECT ?source ?sourceLabels ?target ?targetLabels ?relation ?relationDirection ?reference ?referenceDate WHERE {
      GRAPH ?reference {
        ?source ?relation ?target .
      }
      ?reference <info:date> ?referenceDate .
      ?relation a <info:SocialRelation> .
      ?relation <http://www.w3.org/1999/02/22-rdf-syntax-ns#direction> ?relationDirection .
      ?source <https://d-nb.info/standards/elementset/gnd#preferredNameForThePerson> ?sourceLabels .
      ?target <https://d-nb.info/standards/elementset/gnd#preferredNameForThePerson> ?targetLabels .
      ${filters.join("\n  ")}
    }`.trim();
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method !== "GET" || url.pathname !== "/api/v1/search") {
    res.writeHead(404, {
      "Content-Type": "application/json",
    });

    res.end(JSON.stringify({ error: "Not found" }));
    return;
  }

  const query = buildQuery(url.searchParams);
  const format = url.searchParams.get("format") || "json";

  if (!["json", "csv"].includes(format)) {
    res.writeHead(400, {
      "Content-Type": "application/json; charset=utf-8",
    });

    res.end(
      JSON.stringify({
        error: "Invalid format",
        allowed: ["json", "csv"],
      })
    );

    return;
  }

  const acceptType = format === "csv" ? "text/csv" : "application/sparql-results+json";

  console.log("\n--- SPARQL query ---");
  console.log(query);
  console.log("--------------------\n");

  try {
    const sparqlUrl = new URL(SPARQL_ENDPOINT);
    sparqlUrl.searchParams.set("query", query);

    const response = await fetch(sparqlUrl, {
      headers: {
        Accept: acceptType,
      },
    });

    const body = await response.text();

    if (!response.ok) {
      res.writeHead(502, {
        "Content-Type": "application/json; charset=utf-8",
      });

      res.end(
        JSON.stringify({
          error: "QLever returned an error",
          status: response.status,
          body: body,
        })
      );

      return;
    }

    res.writeHead(200, {
      "Content-Type": `${acceptType}; charset=utf-8`,
    });

    res.end(body);
  } catch (error) {
    console.error(error);

    res.writeHead(502, {
      "Content-Type": "application/json; charset=utf-8",
    });

    res.end(
      JSON.stringify({
        error: "Could not reach QLever",
        message: error.message,
      })
    );
  }

});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Listening on http://localhost:${PORT}`);
});

// variable declaration
// default file = "clemens_brentano_snac.json";

// flow declaration
"clemens_brentano_snac.json"
| open-file
| as-records
| decode-json
| fix("create_links_snac.fix")
| stream-to-triples(redirect="true")
| template("<${s}> <${p}> <${o}> .")
| write("stdout");
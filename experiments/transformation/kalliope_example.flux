// variable declaration
// default file = "clemens_brentano_kalliope.xml";

// flow declaration
"clemens_brentano_kalliope.xml"
| open-file
| decode-xml
| handle-generic-xml
| fix("create_links_kalliope.fix")
| stream-to-triples(redirect="true")
| template("<${s}> ${p} <${o}> .")
| write("clemens_brentano_kalliope.nt");
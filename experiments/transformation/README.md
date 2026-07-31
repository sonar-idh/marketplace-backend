# Metafacture
Metafacture is a combination many funtions aka flux and fix commands that are commonly used in library metadata.

Flux: Flow orchestrator, similiar to piping in Linux
Fix: transformer, that changes the data format

The flux file calls fix in its flow.

The goal is to understand the transformation flow in SoNAR by creating some examples using Kalliope, GND, SNAC data and fusing them together. Then the frontend should get all the data with a single API call to backend.

## Setup
Install by following this: https://metafacture.github.io/metafacture-documentation/docs/Getting-Started.html

Metafacture provides an interactive playground to test things with different examples.

## Examples

Examples are focused on creating a triple from Kalliope and SNAC to merge them based on Authority ID.

### Kalliope
- [Flux File](./kalliope_example.flux)
- [Fix File](./create_links_kalliope.fix)

*Note: In this example both metafacture installation and flux files are in the same folder*
```
# Run
./metafacture/flux.sh kalliope_example.flux
```
```
# Output Triple
<https://kalliope-verbund.info/DE-611-BF-39849> owl:sameAs <https://d-nb.info/gnd/118515055> .
```

### SNAC
- [Flux File](./snac_example.flux)
- [Fix File](./create_links_snac.fix)
```
# Run
./metafacture/flux.sh snac_example.flux
```
```
# Output Triples
<https://d-nb.info/gnd/118515055> <owl:sameAs> <https://viaf.org/viaf/73863902> .
<https://d-nb.info/gnd/118515055> <owl:sameAs> <https://www.wikidata.org/entity/Q57235> .
<https://d-nb.info/gnd/118515055> <owl:sameAs> <https://www.worldcat.org/identities/lccn-n80005077> .
<https://d-nb.info/gnd/118515055> <owl:sameAs> <https://id.loc.gov/authorities/n80005077> .

```

As the DNB GND ID is linked with VIAF and other external data sources, after indexing, it is possible to get data from all the sources that are connected to a Authority ID file.

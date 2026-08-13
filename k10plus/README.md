# MVP: K10Plus MARC --> SoNAR HNA Graph

![Coverage](https://img.shields.io/badge/coverage-84%25-brightgreen)

## Data Transformation Pipeline

  ```mermaid
flowchart LR
    subgraph MARC2BIBFRAME[MARC2BIBFRAME Converter XSLT]
        direction LR
        m1[Preprocessing: format and split] --> m2[MARC to BIBFRAME]
    end
    subgraph RDF2CIDOC[BIBFRAME RDF to CIDOC Converter]
        direction LR
        f --> t2[/HNR Graph/]
    end
    subgraph BIBFRAME2[BIBFRAME Graph]
        direction LR
    m2 --> r[/RDF/]
    r -->|rapper| t[/.ttl/]

    end

    s1[/K10Plus MARC XML/] --> m1
    t --> f[Data Filter: SPARQL Construct]

```
## Setup
- Clone the `marc2bibframe2` converter: `git clone https://github.com/lcnetdev/marc2bibframe2`

### Transformation pipeline for bigger dataset.
- The data is converted to smaller chunks.
- This bash script is used to convert from MARC to CIDOC.
- Validating the graph using shacl.
```bash
# Run bash script to directly convert to CIDOC-CRM : ~30 mins for 60k records
# pipes xslt, rapper and bibframe2cidoc python script
bash marc2cidoc.sh
```
```bash
# Graph Validation ~ 5mins for 60k records
uv run pyshacl -s data/shacl.ttl -m -i rdfs -a -j -f human data/cidoc/kxp_chunk_*.ttl > shacl_errors.txt
```
### Run the transformation pipeline (example using `schumann.xml` inside the `k10plus/` folder):
```bash
# Format the xml file (OPTIONAL: easy for visual debugging)
xmllint --format data/schumann.xml > data/formatted.xml

# Split the xml file into single records
xsltproc marc2bibframe2/xsl/ConvSpec-Preprocess0-Splitting.xsl data/formatted.xml > data/schumann_preprocessed.xml

# Convert the xml file to bibframe
xsltproc marc2bibframe2/xsl/marc2bibframe2.xsl data/schumann_preprocessed.xml > data/schumann_bib.xml

# Convert the xml file to ttl
rapper data/schumann_bib.xml -o turtle > data/schumann_bib.ttl

# Converts BIBFRAME to SoNAR CIDOC-CRM
python3 bibframe_to_cidoc.py -i data/schumann_bib.ttl -o data/schumann_cidoc.ttl
```

## Code Quality & Linting

#### Ruff
Ruff is used for quick code linting and formatting.
Run from the repository root:
```bash
# Lint checks
uvx ruff check k10plus/

# Automatically fix lint errors
uvx ruff check --fix k10plus/

# Format code styling
uvx ruff format k10plus/
```

#### Pre-commit
The repository includes a `pre-commit` configuration to validate styling and code quality before every git commit.

1. **Register the pre-commit hooks**:
   ```bash
   uv run --project k10plus pre-commit install
   ```

2. **Manually run all hooks** on all files:
   ```bash
   uv run --project k10plus pre-commit run --all-files
   ```

## Tests & Coverage

Tests are managed using `pytest` and virtual environment isolation is handled by `uv`.

#### Running Tests from inside the `k10plus/` folder (Recommended)

1. Change directory to the project directory:
   ```bash
   cd k10plus
   ```
2. Run all tests:
   ```bash
   uv run pytest
   ```
3. Run tests with output logs suppressed/warnings-only:
   ```bash
   uv run pytest --log-level=WARNING
   ```

#### Test Coverage

To run the test suite and view a detailed statement-by-statement coverage report:

```bash
# Terminal summary with missing line numbers
uv run pytest --cov=. --cov-report=term-missing

# Generate interactive HTML report (saved to htmlcov/index.html)
uv run pytest --cov=. --cov-report=html
```

#### Running Full/Slow Tests

By default, slow full-dataset tests are deselected for performance. To execute all tests including slow ones:

```bash
uv run pytest -m slow
```

#### Running Tests from the Repository Root

If you prefer to stay at the repository root (`marketplace-backend`), you can run:
```bash
uv run --project k10plus pytest --log-level=WARNING
```

#### Regenerating Regression Test Data

If data structure changes are intentional, you can regenerate the reference test outputs using the `--force-regen` flag:
```bash
# From inside the k10plus directory
uv run pytest --force-regen
```
```bash
# Running specific test file
uv run pytest tests/test_marc_dump_analysis.py --force-regen
```

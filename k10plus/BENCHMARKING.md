
## Pipeline Benchmarks

### 2-Chunk Test Run Comparison (`kxp_chunk_182`, `kxp_chunk_183`)

Measured on 2 chunks (`kxp_chunk_182`, `kxp_chunk_183`) with **2 parallel jobs** (`--jobs 2`) using `rdflib`.

- **Data Size Transformation (per chunk)**:
  - **MARC XML**: ~50 MB
  - **BIBFRAME Turtle**: ~25 MB (~800k–980k triples)
  - **CIDOC CRM Turtle**: ~2 MB (~33.8k triples)

| XSLT Engine | Pipeline Wall Time | User Time | Sys Time | SHACL Validation Time | Speedup vs xsltproc |
|---|---:|---:|---:|---:|---:|
| **Saxon-HE (no preprocessing)** | **1m 13.15s** | 3m 32.05s | 0m 06.13s | 0m 10.14s | **1.39× faster** |
| **Saxon-HE (with preprocessing)** | **1m 16.21s** | 4m 20.37s | 0m 07.81s | 0m 10.14s | **1.33× faster** |
| **xsltproc** | 1m 41.67s | 3m 13.25s | 0m 08.93s | 0m 10.24s | 1.00× |

*Note: Removing the XSLT preprocessing step (`ConvSpec-Preprocess0-Splitting.xsl`) in Saxon-HE saves ~3 seconds of wall time and ~48 seconds of user CPU time per 2 chunks.*

---

### Single Chunk Detailed Breakdown (`kxp_chunk_183`)
Measured on a single chunk (`kxp_chunk_183`) — **698,734 triples**, 3 SPARQL CONSTRUCT queries.
Full pipeline: `MARC XML → XSLT → rapper → tee → bibframe_to_cidoc.py`

### RDFLib Store: Oxigraph vs Default (Python step only)

| Phase | Oxigraph | rdflib `default` | Speedup |
|---|---:|---:|---:|
| Parse (698K triples) | 28.8s | 24.7s | 1.2× |
| Q1 titleInfo | 24.0s | 5.3s | **4.5×** |
| Q2 Agents | 32.8s | 9.8s | **3.3×** |
| Q3 Timestamp | 16.5s | 4.0s | **4.1×** |
| Serialize | 1.4s | 1.4s | 1.0× |
| **Total** | **1m 44s** | **0m 46s** | **2.3×** |

→ `rdflib default` is the default store in `bibframe_to_cidoc.py`. Use `--store Oxigraph` to switch.

### Full Pipeline: Saxon-HE vs xsltproc

Both using `rdflib default` store, GNU Parallel `--jobs 4`.

| XSLT Engine | Wall time | User time | user/real |
|---|---:|---:|---:|
| **Saxon-HE** (2× JVM) | **3m 38s** | 18m 26s | 5.1× |
| xsltproc | 4m 29s | 13m 35s | 3.0× |

Saxon-HE is ~30% faster at XSLT. The higher `user/real` ratio for Saxon reflects JVM internal threads (JIT, GC).

### Extrapolation to 184 Chunks (4 parallel jobs)

| Configuration | Per chunk | **4 jobs ETA** |
|---|---:|---:|
| Saxon-HE + rdflib default | 3m 38s | **~2h 47m** |
| xsltproc + rdflib default | 4m 29s | **~3h 27m** |
| Saxon-HE + Oxigraph (old) | ~4m 36s | **~3h 32m** |

> Memory note: rdflib workers hold ~700K triples in RAM each. At 4 jobs expect ~6–8 GB peak.
> The `--memfree 2G` guard in `parallel` throttles automatically if memory is tight.

---

## MARC Dump Analysis Benchmarks

### Single Chunk Detailed Comparison (`kxp_chunk_183.xml` — 2,601 Records)

Measured on a single 50 MB chunk (`kxp_chunk_183.xml`) containing **2,601 MARC records**.

| Script Version | Processing Time | Throughput | Speedup vs Baseline |
|---|---:|---:|---:|
| **`pymarc`** (Baseline) | **9.76s** | 267 rec/s | 1.00× |
| **`lxml`** | **3.57s** | 729 rec/s | **2.73× faster** |

---

### 2-Chunk Parallel Comparison (2 Workers — 6,816 Records)

Measured on **2 chunks** (`data/chunks/test/`) containing **6,816 MARC records** using **2 parallel workers**.

| Script Version | Workers / Cores | Wall Time | Throughput | Speedup vs Baseline |
|---|---:|---:|---:|---:|
| **`pymarc`** (Baseline) | 2 Workers | **9.012s** | 756 rec/s | 1.00× |
| **`lxml`** | 2 Workers | **3.72s** | 1,834 rec/s | **2.42× faster** |

---

### 184 Chunks Performance Profile (`pymarc` vs `lxml`)

Measured across all **184 chunk files** (`data/chunks/*.xml`, ~9.2 GB total MARC XML data, >1,000,000 records).

| Script / Engine | Parser & Execution Model | Workers / Cores | Wall Time | Speedup vs Baseline |
|---|---|---:|---:|---:|
| **`pymarc`** (Baseline) | Pure Python `pymarc` + per-record IPC queue logging + dict pickling | 4 Workers | **~40m – 45m** | 1.00× |
| **`lxml`** | `lxml.etree.iterparse` (C libxml2) + node memory clearing (`fast_iter`) | 1 Worker | **~2m 30s** | **~16× faster** |
| **`lxml`** (Parallel) | `lxml` streaming + multiprocessing + summary `Counter` IPC returns | 4 Workers | **~35s** | **~70× faster** |
| **`lxml`** (Parallel) | `lxml` streaming + multiprocessing + summary `Counter` IPC returns | 8 Workers | **~18s** | **~130× faster** |
| **`lxml`** (36 Tasks / 40.9M Records) | `lxml` streaming + multiprocessing (36 chunks, 40,977,374 records) | 12 Cores | **28m 14s** (1694.48s, 24,183 rec/s) | N/A |

### Bottleneck Analysis & Optimization Breakdown

1. **DOM Instantiation vs. Streaming C-Parsers**:
   - `pymarc` uses `pymarc.map_xml`, creating full Python objects for every record, subfield, and controlfield.
   - `lxml` uses C-based `lxml.etree.iterparse` and purges nodes (`elem.clear()`, deleting element siblings) immediately after processing to maintain constant memory usage (<100 MB per worker).

2. **IPC Logging Overhead**:
   - `pymarc` sends `logger.info()` log messages across a `multiprocessing.Queue` for every single record and matching tag, saturating IPC channels.
   - `lxml` aggregates stats locally in `Counter()` instances and returns only the final counter summary per worker.

3. **Multiprocessing Scaling**:
   - Because XML chunks are fully independent files, processing all 184 chunks across multiple CPU cores scales linearly without shared state overhead.

---

## Decompression Performance (`pigz` vs `gunzip`)

Measured on `SA-MARC-verbund-001.xml.gz` decompressing directly to file (`> test.xml`).

| Tool | Execution Model | Real (Wall Time) | User CPU Time | Sys CPU Time | Speedup vs gunzip |
|---|---|---:|---:|---:|---:|
| **`gunzip -c`** | Single-threaded | **1m 4.917s** (64.9s) | 46.985s | 11.779s | 1.00× |
| **`pigz -dc`** | Multi-threaded | **16.772s** | 18.517s | 14.563s | **3.87× faster** |

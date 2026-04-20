# Mnemosyne

**DKG-native concept-mining paranet.** A small, deterministic Python toolkit for building, querying, and anchoring verifiable Knowledge Assets on the [OriginTrail Decentralized Knowledge Graph (DKG v9)](https://docs.origintrail.io/).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Status: v0.1.0](https://img.shields.io/badge/Status-v0.1.0-green.svg)](#roadmap)
[![Tests: 26/26](https://img.shields.io/badge/Tests-26%2F26-brightgreen.svg)](./tests)

Named after **Μνημοσύνη** — the Greek goddess of memory and mother of the nine Muses — Mnemosyne is a library for durable, verifiable memory shared across AI agents.

---

## Table of contents

- [Why Mnemosyne](#why-mnemosyne)
- [Install](#install)
- [60-second example](#60-second-example)
- [Concepts](#concepts)
- [Architecture](#architecture)
- [Core API](#core-api)
- [SPARQL](#sparql)
- [Anchoring on OriginTrail](#anchoring-on-origintrail)
- [The nine Muses](#the-nine-muses)
- [Project layout](#project-layout)
- [Development](#development)
- [Design invariants](#design-invariants)
- [Roadmap](#roadmap)
- [Harmonia — planned sibling](#harmonia--planned-sibling)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Why Mnemosyne

Building trustworthy knowledge infrastructure for AI agents requires three things that rarely ship together:

1. **A deterministic content format.** The same facts, submitted by different agents, must produce the same identifier and the same on-chain root. Mnemosyne gives you a binary Merkle tree over canonical N-Triples. Two agents that mine the same concept get the same `KnowledgeAsset.id()` — byte for byte.
2. **A local-first query surface.** You should be able to build, inspect, and query assets before touching a chain. Mnemosyne ships an in-memory [rdflib](https://rdflib.readthedocs.io/) `Dataset` with one named graph per asset, and SPARQL `SELECT` / `ASK` / `CONSTRUCT` across the union.
3. **A transport you can swap.** Integration tests should not need a live blockchain node; production should not need a mock. Mnemosyne's `AnchorClient` takes a pluggable `DkgTransport` — use `NullTransport` offline, `DkgNodeTransport` against a real OriginTrail node.

The library is intentionally small. The core (Triple → Merkle → KnowledgeAsset → Paranet) depends on nothing outside the Python standard library. SPARQL adds `rdflib`. Anchoring lazily imports the OriginTrail `dkg.py` SDK only when you actually publish.

---

## Install

```bash
# Core only (stdlib — Triple, Merkle, KnowledgeAsset, Paranet)
pip install git+https://github.com/Zynerji/Mnemosyne

# Core + SPARQL + JSON-LD/N-Quads codecs
pip install "mnemosyne[rdf] @ git+https://github.com/Zynerji/Mnemosyne"

# Core + everything needed to anchor against a live DKG node
pip install "mnemosyne[dkg] @ git+https://github.com/Zynerji/Mnemosyne"
```

Requires Python 3.11+. Tested on 3.11, 3.12, 3.13, 3.14.

> Mnemosyne is not yet published to PyPI. A `pip install mnemosyne` target will land with v0.2.

---

## 60-second example

```python
from mnemosyne import Triple, KnowledgeAsset
from mnemosyne.rdf import KAStore
from mnemosyne.client import AnchorClient, NullTransport

# 1. Build a Knowledge Asset from RDF triples
ka = KnowledgeAsset(
    paranet="urn:muse:calliope",
    triples=(
        Triple("urn:concept:1",
               "http://www.w3.org/2004/02/skos/core#prefLabel",
               "phi-crystal"),
        Triple("urn:concept:1", "urn:mnem:pool", "reasoning"),
        Triple("urn:concept:1", "urn:mnem:observed_at",
               "2026-04-20T12:00:00Z"),
    ),
)

# 2. The KA id is the Merkle root of its canonical triples
print(ka.id())
# -> '0ad6750eeaf9d23c672ab9eebf14a57ff2db1d60032da2bdb080e6e03dce0f0b'

# 3. Issue and verify a proof for any individual triple
proof = ka.proof_for(ka.triples[0])
assert proof.verify()

# 4. Store it locally and query with SPARQL
store = KAStore()
store.add(ka)
rows = list(store.query(
    'SELECT ?s ?o WHERE { ?s <urn:mnem:pool> ?o }'
))
# -> [(urn:concept:1, reasoning)]

# 5. Anchor it — use NullTransport offline, DkgNodeTransport in prod
client = AnchorClient(transport=NullTransport())
result = client.anchor(ka)
# -> {'status': 'recorded', 'ka_id': '0ad67...', 'paranet': 'urn:muse:calliope', ...}
```

---

## Concepts

Mnemosyne models knowledge at four levels:

### Triple

The atomic unit. An RDF statement `(subject, predicate, object)`. Mnemosyne distinguishes IRIs (prefixed `http://`, `https://`, `urn:`, `did:`, `ipfs://`) from literals automatically, and serializes to canonical [N-Triples](https://www.w3.org/TR/n-triples/) with escape-correct literals.

```python
Triple("urn:concept:1", "urn:mnem:pool", "reasoning")
# -> canonical: <urn:concept:1> <urn:mnem:pool> "reasoning" .
```

### KnowledgeAsset (KA)

A set of triples, a paranet identifier, and a deterministic Merkle root over the canonical triple bytes. The root *is* the KA id — reorder the triples, duplicate them, add them back in a different sequence: the id stays the same. Change a single byte of any triple and the id changes.

Each triple in a KA is independently verifiable against the root via a `MerkleProof` — enabling selective disclosure and efficient verification of subsets.

### Paranet

A named scope that groups related KAs. A `Paranet` carries a `domain`, a consensus threshold `M` (for M-of-N co-signing, relevant once multi-agent coordination lands), and an anchor cadence `N`. In Mnemosyne, paranets are modeled after the nine [Muses](#the-nine-muses) — one per knowledge domain — but you can define any paranet namespace you like (`urn:paranet:biomed`, `urn:paranet:legal`, etc.).

### MerkleProof

A compact path from a specific triple's leaf hash to the KA's Merkle root. `proof.verify()` returns `True` iff the triple really is a member of the KA whose root is recorded in the proof.

---

## Architecture

```
   concept sources
   (LLMs, agents, tools, adapters)
              |
              v  RDF triples
   +-------------------------------------+
   |   Mnemosyne core (stdlib only)      |
   |                                     |
   |   Triple --> KnowledgeAsset         |
   |                  |                  |
   |                  v                  |
   |          Merkle (SHA-256,           |
   |          domain-separated)          |
   +-----+---------------+---------------+
         |               |
         v               v
   +-----------+   +----------------+
   | KAStore   |   | AnchorClient   |
   | (rdflib   |   | codec: JSON-LD |
   | Dataset;  |   |       N-Quads  |
   | SPARQL)   |   | transport:     |
   +-----------+   |  - Null        |
                   |  - DkgNode --+ |
                   +-------------+--+
                                 |
                                 v  JSON-LD
                   +------------------------------+
                   | OriginTrail dkg.py SDK       |
                   | -> DKG v9 node               |
                   | -> Merkle root anchored      |
                   |    on chain (NeuroWeb / etc) |
                   +------------------------------+
```

The **core** (Triple, Merkle, KnowledgeAsset, Paranet) has **no external dependencies** — it will run anywhere Python 3.11 runs, including browser-like constrained environments once WASI support matures.

The **rdf** module imports `rdflib` lazily, so `import mnemosyne` does not require rdflib to be installed unless you use `KAStore`.

The **client** module imports the OriginTrail `dkg.py` SDK lazily — only when you construct `DkgNodeTransport` and actually publish.

---

## Core API

### `Triple`

```python
from mnemosyne import Triple

t = Triple(subject="urn:concept:1",
           predicate="http://www.w3.org/2004/02/skos/core#prefLabel",
           object="phi-crystal")

t.canonical()
# -> b'<urn:concept:1> <http://www.w3.org/2004/02/skos/core#prefLabel> "phi-crystal" .\n'
```

Triples are hashable, frozen dataclasses. They sort lexicographically by their canonical N-Triples form.

### `KnowledgeAsset`

```python
from mnemosyne import KnowledgeAsset

ka = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(triples))

ka.id()                 # 64-hex SHA-256 Merkle root
ka.root()               # 32-byte raw root
ka.canonical_leaves()   # sorted, deduplicated list of canonical triple bytes
ka.proof_for(triple)    # MerkleProof for a specific triple
```

### `MerkleProof`

```python
proof = ka.proof_for(ka.triples[0])
proof.leaf_index        # position in the sorted leaf list
proof.leaf_hash         # SHA-256 of 0x00 || canonical_triple
proof.siblings          # tuple of 32-byte sibling hashes up to the root
proof.root              # 32-byte root (matches ka.root())
proof.verify()          # bool
```

Domain separation: leaves are hashed with a `0x00` prefix, internal nodes with `0x01`, preventing length-extension and second-preimage collisions between leaves and nodes. Odd-count levels duplicate the last node.

### `Paranet`

```python
from mnemosyne import Paranet, MUSE_PARANETS

p = Paranet(id="urn:muse:calliope",
            domain="reasoning",
            consensus_threshold=3,   # M of N signers
            anchor_interval=10)      # batch N KAs before anchoring

MUSE_PARANETS["calliope"]    # -> "reasoning"
```

---

## SPARQL

`KAStore` holds each KA in its own named graph, keyed by `urn:mnemosyne:ka:<ka_id>`. You can query across the union graph, or scope a query to a single KA's graph with a `GRAPH <...>` clause.

### Cross-KA query (union graph)

```python
from mnemosyne.rdf import KAStore

store = KAStore()
store.add(ka_alpha)
store.add(ka_beta)
store.add(ka_gamma)

rows = list(store.query("""
    SELECT ?concept ?pool WHERE {
      ?concept <urn:mnem:pool> ?pool .
      FILTER(?pool = "reasoning")
    }
"""))
```

### Scoped query (single KA)

```python
rows = list(store.query(f"""
    SELECT ?s ?p ?o WHERE {{
      GRAPH <urn:mnemosyne:ka:{ka_alpha.id()}> {{ ?s ?p ?o }}
    }}
"""))
```

### CONSTRUCT / ASK

```python
# ASK: does any KA in the store claim concept:1 is in the reasoning pool?
ask = store.query(
    'ASK { <urn:concept:1> <urn:mnem:pool> "reasoning" }'
)
assert bool(ask)

# CONSTRUCT: build a derived graph of "reasoning concepts"
derived = store.query("""
    CONSTRUCT { ?c <urn:mnem:kind> "reasoning-concept" }
    WHERE    { ?c <urn:mnem:pool> "reasoning" }
""")
```

### Store introspection

```python
store.ka_ids()              # list of KA ids currently in the store
store.triples_for(ka_id)    # iterator of Triple objects in a given KA
len(store)                  # total quad count across all named graphs
```

---

## Anchoring on OriginTrail

The `AnchorClient` is transport-agnostic.

### Offline / testing: `NullTransport`

```python
from mnemosyne.client import AnchorClient, NullTransport

transport = NullTransport()
client = AnchorClient(transport=transport)

client.anchor(ka)
# -> {'status': 'recorded', 'ka_id': ..., 'paranet': ..., 'merkle_root': ...}

# Every call is kept for inspection
transport.calls[0]["envelope"]["public"]   # the JSON-LD assertion
```

`NullTransport` never touches the network and records every call, making it a natural fit for unit tests and CI pipelines.

### Production: `DkgNodeTransport`

```python
from mnemosyne.client import AnchorClient, DkgNodeTransport

transport = DkgNodeTransport(
    endpoint="http://localhost:8900",
    blockchain={
        "name": "hardhat:31337",       # or neuroweb:testnet, base:testnet, ...
        "publicKey": "0x...",
        "privateKey": "0x...",         # or use a signer callback (recommended)
    },
    environment="development",          # or testnet / mainnet
    epochs_num=1,                       # asset lifetime in epochs
)

client = AnchorClient(transport=transport)
result = client.anchor(ka)
# -> {'status': 'published', 'dkg_result': <SDK response>, ...}
```

The `dkg.py` SDK is imported lazily inside `DkgNodeTransport._client()`. If the SDK is not installed, the error message tells you how to install it.

### JSON-LD envelope

Internally, `AnchorClient.anchor(ka)` converts the KA into a JSON-LD envelope:

```python
{
    "public":      <JSON-LD serialization of the triples>,
    "paranet":     "urn:muse:calliope",
    "ka_id":       "<64-hex Merkle root>",
    "merkle_root": "<same — kept explicit for off-chain verification>",
}
```

You can inspect or reshape this envelope yourself via `ka_to_jsonld(ka)` or request N-Quads via `ka_to_nquads(ka)`.

---

## The nine Muses

Mnemosyne ships a default paranet namespace derived from her nine daughters, each mapped to a knowledge domain. The mapping is a convenience; you are free to define any paranets you need.

| Muse           | Domain         | Paranet id               |
|----------------|----------------|--------------------------|
| Calliope       | reasoning      | `urn:muse:calliope`      |
| Clio           | factuality     | `urn:muse:clio`          |
| Erato          | instruction    | `urn:muse:erato`         |
| Euterpe        | calibration    | `urn:muse:euterpe`       |
| Melpomene      | abstention     | `urn:muse:melpomene`     |
| Polyhymnia     | grounding      | `urn:muse:polyhymnia`    |
| Terpsichore    | consistency    | `urn:muse:terpsichore`   |
| Thalia         | sycophancy     | `urn:muse:thalia`        |
| Urania         | distillation   | `urn:muse:urania`        |

```python
from mnemosyne import MUSE_PARANETS
MUSE_PARANETS["urania"]   # -> "distillation"
```

---

## Project layout

```
Mnemosyne/
├── src/mnemosyne/
│   ├── __init__.py          # re-exports: Triple, KnowledgeAsset, Paranet, ...
│   ├── triples.py           # Triple with N-Triples canonicalization
│   ├── merkle.py            # binary SHA-256 Merkle tree, proofs
│   ├── ka.py                # KnowledgeAsset
│   ├── paranet.py           # Paranet + MUSE_PARANETS
│   ├── rdf/
│   │   └── store.py         # KAStore (rdflib Dataset, SPARQL)
│   ├── client/
│   │   ├── codec.py         # ka_to_jsonld, ka_to_nquads
│   │   ├── transport.py     # DkgTransport Protocol, NullTransport, DkgNodeTransport
│   │   └── anchor.py        # AnchorClient
│   └── mining/
│       └── __init__.py      # concept-source adapters (v0.2)
├── tests/
│   ├── test_triples.py
│   ├── test_merkle.py
│   ├── test_ka.py
│   ├── test_rdf_store.py
│   └── test_client.py
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## Development

```bash
git clone https://github.com/Zynerji/Mnemosyne.git
cd Mnemosyne
pip install -e ".[dev]"
pytest
```

The test suite is hermetic. It exercises the full Merkle / KA / SPARQL / codec / anchor pipeline using `NullTransport`; no network, no node, no keys, no chain.

```
26 passed in 0.63s
```

---

## Design invariants

These are enforced by tests and treated as part of the API:

1. **Deterministic id.** `KnowledgeAsset.id()` depends only on the set of triple bytes. Order-independent and duplicate-independent.
2. **Domain separation.** Leaves use `0x00`, internal nodes use `0x01`. A leaf hash cannot collide with a node hash.
3. **Canonical triples.** IRI terms detected by prefix, literals escape-correct, line-terminated — always compatible with standard N-Triples parsers.
4. **Graph isolation.** `KAStore` stores each KA in its own named graph; a KA's triples cannot silently leak into another KA's provenance.
5. **Lazy heavy imports.** `import mnemosyne` never imports `rdflib` or `dkg.py`. Core is stdlib-only.
6. **Transport is swappable.** `AnchorClient` depends only on the `DkgTransport` protocol. You can mock, record, fork, or route however you like.

---

## Roadmap

| Version  | Scope                                                                                          | Status     |
|----------|------------------------------------------------------------------------------------------------|------------|
| v0.0.1   | Core data model (Triple, Merkle, KnowledgeAsset, Paranet)                                      | shipped    |
| v0.1.0   | SPARQL layer (`KAStore`) + DKG anchor client (`AnchorClient` + `NullTransport` + `DkgNodeTransport`) | shipped    |
| v0.2     | Concept-source adapters: pluggable mining backends → streaming triple emitters                 | planned    |
| v0.3     | Live OriginTrail testnet anchoring + epoch-aware `Paranet` policy                              | planned    |
| v0.4     | Paranet policy enforcement (consensus threshold, anchor interval, epoch TTL)                   | planned    |
| v1.0     | Stable API, PyPI release, documentation site                                                   | planned    |

---

## Harmonia — planned sibling

**Harmonia** (Ἁρμονία) — the goddess of harmony and concord — is a planned companion project for multi-agent coordination over Mnemosyne. Harmonia focuses on the parts of the DKG specification that require *consensus* before a KA is anchored:

- Per-agent persistent lineage: who proposed what, when, with what confidence
- Peer-to-peer draft gossip between agents (libp2p transport)
- Threshold signing (FROST) so that a KA is only anchored once M-of-N agents have independently validated it
- Epoch-batched anchoring to amortize on-chain cost

Mnemosyne provides the data substrate (triples, Merkle, KA, Paranet). Harmonia will provide the collective-intelligence substrate on top. Planned home: `github.com/Zynerji/Harmonia`.

---

## Contributing

Issues, discussion, and pull requests are welcome. For larger changes, please open an issue first so we can discuss the direction before you invest time in a PR.

A few norms:

- New features land with tests. The existing suite is hermetic — keep it that way.
- Public API changes (anything in `src/mnemosyne/__init__.py`) are SemVer-governed and should be discussed in an issue first.
- Prefer stdlib over new dependencies in the core. The core is small and should stay that way.

---

## License

[MIT](./LICENSE) © 2026 Christian Knopp.

---

## Acknowledgements

- **[OriginTrail](https://origintrail.io/)** for the Decentralized Knowledge Graph and the `dkg.py` SDK.
- **[rdflib](https://rdflib.readthedocs.io/)** for a beautiful RDF and SPARQL implementation in Python.
- The Muses, for the nine-fold partition of knowledge — a structure that has outlasted empires and still earns its keep.

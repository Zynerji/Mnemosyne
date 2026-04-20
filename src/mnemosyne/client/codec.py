from __future__ import annotations
import json
from typing import Any
from ..ka import KnowledgeAsset
from ..rdf.store import triple_to_rdflib


def ka_to_nquads(ka: KnowledgeAsset) -> str:
    """Emit the KA's triples as canonical N-Quads within the KA's named graph.
    Used when a DKG node accepts N-Quads directly.
    """
    import rdflib
    ctx_iri = f"urn:mnemosyne:ka:{ka.id()}"
    ctx = rdflib.URIRef(ctx_iri)
    ds = rdflib.Dataset()
    g = ds.graph(ctx)
    for t in ka.triples:
        g.add(triple_to_rdflib(t))
    return ds.serialize(format="nquads")


def ka_to_jsonld(ka: KnowledgeAsset) -> dict[str, Any]:
    """Convert a KnowledgeAsset into the envelope expected by an OriginTrail
    DKG publish call. The `public` field carries the JSON-LD assertion;
    auxiliary fields carry Mnemosyne-specific provenance.
    """
    import rdflib
    g = rdflib.Graph()
    for t in ka.triples:
        g.add(triple_to_rdflib(t))
    jsonld_bytes = g.serialize(format="json-ld")
    public = json.loads(jsonld_bytes)
    return {
        "public": public,
        "paranet": ka.paranet,
        "ka_id": ka.id(),
        "merkle_root": ka.root().hex(),
    }

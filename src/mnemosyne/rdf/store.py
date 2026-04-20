from __future__ import annotations
from typing import Iterable, Iterator
from ..triples import Triple, _IRI_PREFIXES
from ..ka import KnowledgeAsset


def _term(s: str):
    import rdflib
    if s.startswith(_IRI_PREFIXES):
        return rdflib.URIRef(s)
    return rdflib.Literal(s)


def triple_to_rdflib(t: Triple) -> tuple:
    return (_term(t.subject), _term(t.predicate), _term(t.object))


def _rdflib_term_to_str(term) -> str:
    import rdflib
    if isinstance(term, rdflib.URIRef):
        return str(term)
    return str(term)


class KAStore:
    """RDF store for Knowledge Assets. Each KA gets its own named graph,
    keyed by urn:mnemosyne:ka:<ka_id>, so SPARQL queries can filter by
    KA provenance or query the union graph.
    """

    def __init__(self) -> None:
        import rdflib
        self._ds = rdflib.Dataset(default_union=True)

    def add(self, ka: KnowledgeAsset) -> str:
        import rdflib
        ka_id = ka.id()
        ctx = rdflib.URIRef(f"urn:mnemosyne:ka:{ka_id}")
        g = self._ds.graph(ctx)
        for t in ka.triples:
            g.add(triple_to_rdflib(t))
        return ka_id

    def add_many(self, kas: Iterable[KnowledgeAsset]) -> list[str]:
        return [self.add(ka) for ka in kas]

    def query(self, sparql: str):
        return self._ds.query(sparql)

    def triples_for(self, ka_id: str) -> Iterator[Triple]:
        import rdflib
        ctx = rdflib.URIRef(f"urn:mnemosyne:ka:{ka_id}")
        g = self._ds.graph(ctx)
        for s, p, o in g:
            yield Triple(str(s), str(p), str(o))

    def __len__(self) -> int:
        return sum(1 for _ in self._ds.quads((None, None, None, None)))

    def ka_ids(self) -> list[str]:
        prefix = "urn:mnemosyne:ka:"
        out: list[str] = []
        for ctx in self._ds.graphs():
            s = str(ctx.identifier)
            if s.startswith(prefix):
                out.append(s[len(prefix):])
        return sorted(set(out))

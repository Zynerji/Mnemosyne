import pytest

pytest.importorskip("rdflib")

from mnemosyne import Triple, KnowledgeAsset
from mnemosyne.rdf import KAStore


def _ka_concept(cid: str, label: str, pool: str) -> KnowledgeAsset:
    return KnowledgeAsset(
        paranet=f"urn:muse:calliope",
        triples=(
            Triple(f"urn:concept:{cid}", "http://www.w3.org/2004/02/skos/core#prefLabel", label),
            Triple(f"urn:concept:{cid}", "urn:mnem:pool", pool),
        ),
    )


def test_add_single_ka_and_iterate():
    store = KAStore()
    ka = _ka_concept("1", "phi-crystal", "reasoning")
    ka_id = store.add(ka)
    assert ka_id == ka.id()
    triples = list(store.triples_for(ka_id))
    assert len(triples) == 2


def test_ka_ids_round_trip():
    store = KAStore()
    ka_a = _ka_concept("1", "phi-crystal", "reasoning")
    ka_b = _ka_concept("2", "silver-ratio", "calibration")
    store.add_many([ka_a, ka_b])
    assert set(store.ka_ids()) == {ka_a.id(), ka_b.id()}


def test_sparql_select_across_kas():
    store = KAStore()
    store.add(_ka_concept("1", "phi-crystal", "reasoning"))
    store.add(_ka_concept("2", "silver-ratio", "calibration"))
    store.add(_ka_concept("3", "bronze-pendulum", "reasoning"))

    rows = list(store.query("""
        SELECT ?s WHERE {
          ?s <urn:mnem:pool> "reasoning" .
        }
    """))
    subjects = {str(r[0]) for r in rows}
    assert subjects == {"urn:concept:1", "urn:concept:3"}


def test_sparql_filter_by_ka_named_graph():
    store = KAStore()
    ka_a = _ka_concept("1", "phi-crystal", "reasoning")
    ka_b = _ka_concept("2", "silver-ratio", "calibration")
    store.add(ka_a)
    store.add(ka_b)

    ka_a_graph = f"urn:mnemosyne:ka:{ka_a.id()}"
    rows = list(store.query(f"""
        SELECT ?s ?o WHERE {{
          GRAPH <{ka_a_graph}> {{ ?s <urn:mnem:pool> ?o }}
        }}
    """))
    assert len(rows) == 1
    assert str(rows[0][0]) == "urn:concept:1"
    assert str(rows[0][1]) == "reasoning"


def test_len_counts_quads():
    store = KAStore()
    store.add(_ka_concept("1", "phi-crystal", "reasoning"))
    store.add(_ka_concept("2", "silver-ratio", "calibration"))
    assert len(store) == 4

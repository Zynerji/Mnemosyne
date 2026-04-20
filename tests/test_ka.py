import pytest
from mnemosyne import Triple, KnowledgeAsset


def _sample_triples() -> list[Triple]:
    return [
        Triple("urn:concept:1", "http://www.w3.org/2004/02/skos/core#prefLabel", "phi-crystal"),
        Triple("urn:concept:1", "urn:pool", "reasoning"),
        Triple("urn:concept:1", "urn:observed_at", "2026-04-20T12:00:00Z"),
    ]


def test_id_is_64_hex_chars():
    ka = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(_sample_triples()))
    kid = ka.id()
    assert len(kid) == 64
    assert all(c in "0123456789abcdef" for c in kid)


def test_id_is_order_independent():
    t = _sample_triples()
    a = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(t))
    b = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(reversed(t)))
    assert a.id() == b.id()


def test_id_is_duplicate_independent():
    t = _sample_triples()
    a = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(t))
    b = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(t + [t[0]]))
    assert a.id() == b.id()


def test_id_changes_with_any_triple_change():
    t = _sample_triples()
    a = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(t))
    t2 = list(t)
    t2[0] = Triple(t2[0].subject, t2[0].predicate, t2[0].object + "x")
    b = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(t2))
    assert a.id() != b.id()


def test_proof_for_every_triple_verifies():
    t = _sample_triples()
    ka = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(t))
    for triple in t:
        p = ka.proof_for(triple)
        assert p.verify()
        assert p.root.hex() == ka.id()


def test_proof_for_unknown_triple_raises():
    ka = KnowledgeAsset(paranet="urn:muse:calliope", triples=tuple(_sample_triples()))
    with pytest.raises(KeyError):
        ka.proof_for(Triple("urn:nope", "urn:p", "x"))

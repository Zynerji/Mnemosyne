import json
import pytest

pytest.importorskip("rdflib")

from mnemosyne import Triple, KnowledgeAsset
from mnemosyne.client import (
    ka_to_jsonld,
    ka_to_nquads,
    NullTransport,
    AnchorClient,
)


def _sample_ka() -> KnowledgeAsset:
    return KnowledgeAsset(
        paranet="urn:muse:calliope",
        triples=(
            Triple("urn:concept:1", "http://www.w3.org/2004/02/skos/core#prefLabel", "phi-crystal"),
            Triple("urn:concept:1", "urn:mnem:pool", "reasoning"),
        ),
    )


def test_ka_to_jsonld_shape():
    env = ka_to_jsonld(_sample_ka())
    assert env["paranet"] == "urn:muse:calliope"
    assert env["ka_id"] == _sample_ka().id()
    assert env["merkle_root"] == _sample_ka().root().hex()
    assert "public" in env
    # JSON-LD should be serializable and non-empty
    assert json.dumps(env["public"])
    assert env["public"]


def test_ka_to_nquads_contains_named_graph():
    nq = ka_to_nquads(_sample_ka())
    ka_id = _sample_ka().id()
    assert f"urn:mnemosyne:ka:{ka_id}" in nq
    assert "urn:concept:1" in nq
    assert "phi-crystal" in nq


def test_null_transport_records_publish():
    t = NullTransport()
    client = AnchorClient(transport=t)
    ka = _sample_ka()
    result = client.anchor(ka)
    assert result["status"] == "recorded"
    assert result["ka_id"] == ka.id()
    assert result["paranet"] == "urn:muse:calliope"
    assert len(t.calls) == 1
    assert t.calls[0]["envelope"]["ka_id"] == ka.id()


def test_null_transport_batch():
    t = NullTransport()
    client = AnchorClient(transport=t)
    kas = [_sample_ka(), _sample_ka()]  # same content → same id, dedup happens on-chain
    results = client.anchor_batch(kas)
    assert len(results) == 2
    assert len(t.calls) == 2


def test_dkg_node_transport_lazy_import_error():
    from mnemosyne.client import DkgNodeTransport
    tr = DkgNodeTransport(endpoint="http://localhost:8900", blockchain={"name": "hardhat:31337"})
    # Calling publish without the dkg.py SDK present must raise a clear ImportError
    with pytest.raises(ImportError, match="dkg.py SDK"):
        tr.publish({"public": {}, "ka_id": "x", "paranet": "y", "merkle_root": "z"})

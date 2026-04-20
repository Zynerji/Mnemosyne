import pytest
from mnemosyne import merkle_root, issue_proof, leaf_hash, node_hash


def test_empty_raises():
    with pytest.raises(ValueError):
        merkle_root([])


def test_single_leaf_root_is_leaf_hash():
    assert merkle_root([b"a"]) == leaf_hash(b"a")


def test_two_leaves():
    assert merkle_root([b"a", b"b"]) == node_hash(leaf_hash(b"a"), leaf_hash(b"b"))


def test_odd_leaf_count_duplicates_last():
    la, lb, lc = leaf_hash(b"a"), leaf_hash(b"b"), leaf_hash(b"c")
    expected = node_hash(node_hash(la, lb), node_hash(lc, lc))
    assert merkle_root([b"a", b"b", b"c"]) == expected


def test_proof_round_trip_all_indices():
    leaves = [f"leaf-{i}".encode() for i in range(7)]
    for i in range(len(leaves)):
        p = issue_proof(leaves, i)
        assert p.verify(), f"proof for index {i} failed"


def test_proof_rejects_wrong_root():
    leaves = [b"a", b"b", b"c"]
    p = issue_proof(leaves, 1)
    tampered = type(p)(
        leaf_index=p.leaf_index,
        leaf_hash=p.leaf_hash,
        siblings=p.siblings,
        root=b"\x00" * 32,
    )
    assert not tampered.verify()


def test_proof_index_out_of_range():
    with pytest.raises(IndexError):
        issue_proof([b"a"], 5)

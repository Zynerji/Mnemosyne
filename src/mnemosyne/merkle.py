from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

_LEAF_PREFIX = b"\x00"
_NODE_PREFIX = b"\x01"


def leaf_hash(data: bytes) -> bytes:
    return sha256(_LEAF_PREFIX + data).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return sha256(_NODE_PREFIX + left + right).digest()


def _build_levels(leaves: Sequence[bytes]) -> list[list[bytes]]:
    if not leaves:
        raise ValueError("cannot build merkle tree with zero leaves")
    level = [leaf_hash(b) for b in leaves]
    levels = [level]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(node_hash(left, right))
        level = next_level
        levels.append(level)
    return levels


def merkle_root(leaves: Sequence[bytes]) -> bytes:
    return _build_levels(leaves)[-1][0]


@dataclass(frozen=True)
class MerkleProof:
    leaf_index: int
    leaf_hash: bytes
    siblings: tuple[bytes, ...]
    root: bytes

    def verify(self) -> bool:
        h = self.leaf_hash
        idx = self.leaf_index
        for sib in self.siblings:
            h = node_hash(h, sib) if idx % 2 == 0 else node_hash(sib, h)
            idx //= 2
        return h == self.root


def issue_proof(leaves: Sequence[bytes], index: int) -> MerkleProof:
    if not (0 <= index < len(leaves)):
        raise IndexError(f"leaf index {index} out of range [0, {len(leaves)})")
    levels = _build_levels(leaves)
    siblings: list[bytes] = []
    idx = index
    for level in levels[:-1]:
        if idx % 2 == 0:
            sib_idx = idx + 1 if idx + 1 < len(level) else idx
        else:
            sib_idx = idx - 1
        siblings.append(level[sib_idx])
        idx //= 2
    return MerkleProof(
        leaf_index=index,
        leaf_hash=levels[0][index],
        siblings=tuple(siblings),
        root=levels[-1][0],
    )

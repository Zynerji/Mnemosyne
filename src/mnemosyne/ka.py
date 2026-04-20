from __future__ import annotations
from dataclasses import dataclass
from .triples import Triple
from .merkle import MerkleProof, _build_levels, issue_proof


@dataclass(frozen=True)
class KnowledgeAsset:
    paranet: str
    triples: tuple[Triple, ...]

    def canonical_leaves(self) -> list[bytes]:
        # Deduplicate + sort so set-equivalent triple bundles produce the same root.
        unique = {t.canonical() for t in self.triples}
        return sorted(unique)

    def root(self) -> bytes:
        return _build_levels(self.canonical_leaves())[-1][0]

    def id(self) -> str:
        return self.root().hex()

    def proof_for(self, triple: Triple) -> MerkleProof:
        leaves = self.canonical_leaves()
        target = triple.canonical()
        try:
            idx = leaves.index(target)
        except ValueError as e:
            raise KeyError(f"triple not in KA: {triple}") from e
        return issue_proof(leaves, idx)

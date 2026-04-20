from __future__ import annotations
from dataclasses import dataclass

_IRI_PREFIXES = ("http://", "https://", "urn:", "did:", "ipfs://")


def _encode_term(t: str) -> str:
    if t.startswith(_IRI_PREFIXES):
        return f"<{t}>"
    escaped = (
        t.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


@dataclass(frozen=True, order=True)
class Triple:
    subject: str
    predicate: str
    object: str

    def canonical(self) -> bytes:
        return (
            f"{_encode_term(self.subject)} "
            f"{_encode_term(self.predicate)} "
            f"{_encode_term(self.object)} .\n"
        ).encode("utf-8")

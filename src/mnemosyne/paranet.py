from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Paranet:
    id: str
    domain: str
    consensus_threshold: int
    anchor_interval: int

    def __post_init__(self) -> None:
        if self.consensus_threshold < 1:
            raise ValueError("consensus_threshold M must be >= 1")
        if self.anchor_interval < 1:
            raise ValueError("anchor_interval N must be >= 1")


MUSE_PARANETS: dict[str, str] = {
    "calliope": "reasoning",
    "clio": "factuality",
    "erato": "instruction",
    "euterpe": "calibration",
    "melpomene": "abstention",
    "polyhymnia": "grounding",
    "terpsichore": "consistency",
    "thalia": "sycophancy",
    "urania": "distillation",
}

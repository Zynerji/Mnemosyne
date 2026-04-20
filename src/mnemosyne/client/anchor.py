from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable
from ..ka import KnowledgeAsset
from .codec import ka_to_jsonld
from .transport import DkgTransport


@dataclass
class AnchorClient:
    transport: DkgTransport

    def anchor(self, ka: KnowledgeAsset) -> dict[str, Any]:
        envelope = ka_to_jsonld(ka)
        return self.transport.publish(envelope)

    def anchor_batch(self, kas: Iterable[KnowledgeAsset]) -> list[dict[str, Any]]:
        return [self.anchor(ka) for ka in kas]

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol


class DkgTransport(Protocol):
    def publish(self, envelope: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class NullTransport:
    """In-memory transport. Records every publish call. Use in tests and
    offline development — no network, no chain, no node required.
    """
    calls: list[dict[str, Any]] = field(default_factory=list)

    def publish(self, envelope: dict[str, Any]) -> dict[str, Any]:
        record = {
            "status": "recorded",
            "ka_id": envelope.get("ka_id"),
            "paranet": envelope.get("paranet"),
            "merkle_root": envelope.get("merkle_root"),
        }
        self.calls.append({"envelope": envelope, "result": record})
        return record


@dataclass
class DkgNodeTransport:
    """Thin adapter over the OriginTrail dkg.py SDK.

    The SDK is imported lazily so Mnemosyne stays usable without it.
    Install the optional extra to get the required packages:
        pip install mnemosyne[dkg]

    Expected init config for dkg.py (passed through to the SDK unchanged):
        endpoint:   http URL of the node
        blockchain: { name, publicKey, privateKey } for signing
        environment: one of {development, testnet, mainnet}
    """
    endpoint: str
    blockchain: dict[str, Any]
    environment: str = "development"
    epochs_num: int = 1
    _sdk: Any = field(default=None, init=False, repr=False)

    def _client(self):
        if self._sdk is None:
            try:
                from dkg import DKG
            except ImportError as e:
                raise ImportError(
                    "dkg.py SDK not installed. `pip install mnemosyne[dkg]` "
                    "plus the OriginTrail SDK package."
                ) from e
            self._sdk = DKG({
                "environment": self.environment,
                "endpoint": self.endpoint,
                "blockchain": self.blockchain,
            })
        return self._sdk

    def publish(self, envelope: dict[str, Any]) -> dict[str, Any]:
        sdk = self._client()
        assertion = {"public": envelope["public"]}
        result = sdk.asset.create(assertion, epochs_num=self.epochs_num)
        return {
            "status": "published",
            "ka_id": envelope.get("ka_id"),
            "paranet": envelope.get("paranet"),
            "merkle_root": envelope.get("merkle_root"),
            "dkg_result": result,
        }

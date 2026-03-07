"""Async IntegrationApi — registration endpoint (§9.2)."""

import json
from collections.abc import Awaitable, Callable

from suz_sdk.api.integration import RegisterConnectionResponse
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import Request


class AsyncIntegrationApi:
    """Async client for the integration registration endpoint (§9.2)."""

    def __init__(
        self,
        transport: object,
        oms_id: str,
        signer: BaseSigner | None,
        registration_key: str | None,
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._signer = signer
        self._registration_key = registration_key

    async def register_connection(
        self,
        address: str,
        name: str | None = None,
    ) -> RegisterConnectionResponse:
        """Register an integration installation with СУЗ.

        POST /api/v3/integration/connection?omsId={omsId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, str] = {"address": address}
        if name is not None:
            body_dict["name"] = name

        body_bytes = json.dumps(body_dict, separators=(",", ":"), ensure_ascii=False).encode()

        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._registration_key:
            headers["X-RegistrationKey"] = self._registration_key
        if self._signer:
            headers["X-Signature"] = self._signer.sign_bytes(body_bytes)

        req = Request(
            method="POST",
            path="/api/v3/integration/connection",
            params={"omsId": self._oms_id},
            headers=headers,
            raw_body=body_bytes,
        )
        resp = await transport.request(req)
        body: dict[str, str] = resp.body  # type: ignore[assignment]
        return RegisterConnectionResponse(
            status=body["status"],
            oms_connection=body.get("omsConnection"),
            name=body.get("name"),
            rejection_reason=body.get("rejectionReason"),
        )

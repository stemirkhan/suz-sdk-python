"""Integration registration API client (§9.2).

Implements "Регистрация установки экземпляра интеграционного решения" —
the method for registering an integration installation with СУЗ and
obtaining an ``omsConnection`` UUID.

API specification (§9.2.1, Table 360–364):
    Method:  POST
    URL:     <base_url>/api/v3/integration/connection?omsId={omsId}
    Headers:
        X-Signature:      Detached CMS signature of the request body (required).
                          Not required for pharmaceuticals product group.
        X-RegistrationKey: Registration key issued by CRPT (required).
        Content-Type:     application/json
        Accept:           application/json

    Body:
        { "address": "...", "name": "..." }   (name is optional, 1-256 chars)

    Response 200:
        {
            "status":          "SUCCESS" | "REJECTED",
            "omsConnection":   "<UUID>",        // present when status=SUCCESS
            "name":            "...",           // present when status=SUCCESS
            "rejectionReason": "..."            // present when status=REJECTED
        }

Notes:
    - The request body MUST be signed before sending; the signature covers the
      raw JSON bytes.  This module pre-serializes the body, signs it, and sends
      the bytes verbatim via ``Request.raw_body`` so the signature always
      matches the transmitted bytes.
    - Sandbox registration key: 4344d884-7f21-456c-981e-cd68e92391e8
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import BaseTransport, Request


class RegisterConnectionResponse(BaseModel):
    """Response from the register_connection endpoint (§9.2.1, Table 364).

    Attributes:
        status:           "SUCCESS" or "REJECTED".
        oms_connection:   UUID assigned to the registered installation.
                          Present only when status is SUCCESS.
        name:             Name of the registered installation.
                          Present only when status is SUCCESS.
        rejection_reason: Reason for rejection.
                          Present only when status is REJECTED.
    """

    status: str
    oms_connection: str | None = None
    name: str | None = None
    rejection_reason: str | None = None


@dataclass
class ConnectionInfo:
    """Info about a registered integration connection (§4.4.26)."""

    oms_connection: str
    address: str | None = None
    program_name: str | None = None
    product_groups: list[str] = field(default_factory=list)
    product_version: str | None = None
    vendor_inn: str | None = None


@dataclass
class ListConnectionsResponse:
    """Response from GET /api/v3/integration/connection (§4.4.26)."""

    oms_connection_infos: list[ConnectionInfo]
    total: int


@dataclass
class DeleteConnectionResponse:
    """Response from DELETE /api/v3/integration/connection (§4.4.27)."""

    success: bool


class IntegrationApi:
    """Client for the integration registration endpoint (§9.2).

    Instantiated and owned by SuzClient — callers access it via
    ``client.integration``.

    Args:
        transport:         HTTP transport to use for requests.
        oms_id:            СУЗ instance UUID, sent as the ``omsId`` query param.
        signer:            Signer for the X-Signature header.  Required for
                           most product groups; not required for pharmaceuticals.
        registration_key:  Registration key issued by CRPT.  Passed as the
                           ``X-RegistrationKey`` header.
        get_auth_headers:  Optional callable returning auth headers.  Required
                           for list_connections() and delete_connection().
    """

    def __init__(
        self,
        transport: BaseTransport,
        oms_id: str,
        signer: BaseSigner | None,
        registration_key: str | None,
        get_auth_headers: Callable[[], dict[str, str]] | None = None,
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._signer = signer
        self._registration_key = registration_key
        self._get_auth_headers = get_auth_headers

    def register_connection(
        self,
        address: str,
        name: str | None = None,
    ) -> RegisterConnectionResponse:
        """Register an integration installation with СУЗ.

        Sends POST /api/v3/integration/connection?omsId={omsId}.

        The body is pre-serialized to bytes, optionally signed, and sent
        verbatim so the X-Signature covers the exact bytes transmitted.

        Args:
            address: Physical address of the integration installation.
            name:    Optional name (1-256 chars).  If omitted, the server
                     generates a random UUID name.

        Returns:
            RegisterConnectionResponse with status and omsConnection on success.

        Raises:
            SuzSignatureError:  Signature was rejected (HTTP 413).
            SuzValidationError: Invalid request parameters (HTTP 400).
            SuzAuthError:       Authentication error (HTTP 401).
            SuzApiError:        Other server error.
            SuzTransportError:  Network-level failure.
        """
        body_dict: dict[str, str] = {"address": address}
        if name is not None:
            body_dict["name"] = name

        # Pre-serialize to bytes so we can sign the exact payload transmitted.
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
        resp = self._transport.request(req)

        body: dict[str, str] = resp.body
        return RegisterConnectionResponse(
            status=body["status"],
            oms_connection=body.get("omsConnection"),
            name=body.get("name"),
            rejection_reason=body.get("rejectionReason"),
        )

    def list_connections(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> ListConnectionsResponse:
        """List registered integration connections for the OMS instance.

        GET /api/v3/integration/connection?omsId={omsId}&limit={limit}&offset={offset}

        Args:
            limit:  Maximum number of connections to return.
            offset: Number of connections to skip.

        Returns:
            ListConnectionsResponse with connections and total count.
        """
        auth_headers = self._get_auth_headers() if self._get_auth_headers else {}
        req = Request(
            method="GET",
            path="/api/v3/integration/connection",
            params={
                "omsId": self._oms_id,
                "limit": str(limit),
                "offset": str(offset),
            },
            headers={
                "Accept": "application/json",
                **auth_headers,
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return ListConnectionsResponse(
            oms_connection_infos=[
                self._parse_connection_info(item)
                for item in body.get("omsConnectionInfos", [])
            ],
            total=body["total"],
        )

    def delete_connection(self, oms_connection: str) -> DeleteConnectionResponse:
        """Delete a registered integration connection.

        DELETE /api/v3/integration/connection?omsId={omsId}&omsConnection={omsConnection}

        Args:
            oms_connection: UUID of the connection to delete.

        Returns:
            DeleteConnectionResponse with success flag.
        """
        auth_headers = self._get_auth_headers() if self._get_auth_headers else {}
        req = Request(
            method="DELETE",
            path="/api/v3/integration/connection",
            params={
                "omsId": self._oms_id,
                "omsConnection": oms_connection,
            },
            headers={
                "Accept": "application/json",
                **auth_headers,
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return DeleteConnectionResponse(success=body.get("success", False))

    @staticmethod
    def _parse_connection_info(data: dict[str, Any]) -> ConnectionInfo:
        return ConnectionInfo(
            oms_connection=data["omsConnection"],
            address=data.get("address"),
            program_name=data.get("programName"),
            product_groups=data.get("productGroups") or [],
            product_version=data.get("productVersion"),
            vendor_inn=data.get("vendorInn"),
        )

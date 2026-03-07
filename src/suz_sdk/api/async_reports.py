"""Async ReportsApi — utilisation reports and receipts (§4.4.11–§4.4.19)."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

from suz_sdk.api.reports import (
    ReceiptFilter,
    ReportsApi,
    ReportStatusResponse,
    SearchReceiptsResponse,
    SendUtilisationResponse,
)
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import Request


class AsyncReportsApi:
    """Async client for KM utilisation reports and receipt queries."""

    def __init__(
        self,
        transport: object,
        oms_id: str,
        get_auth_headers: Callable[[], Awaitable[dict[str, str]]],
        signer: BaseSigner | None = None,
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers
        self._signer = signer

    async def send_utilisation(
        self,
        product_group: str,
        sntins: list[str],
        utilisation_type: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> SendUtilisationResponse:
        """Send a KM utilisation report (POST /api/v3/utilisation)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, Any] = {
            "productGroup": product_group,
            "sntins": sntins,
        }
        if utilisation_type is not None:
            body_dict["utilisationType"] = utilisation_type
        if attributes is not None:
            body_dict["attributes"] = attributes

        raw_body = json.dumps(body_dict, ensure_ascii=False).encode()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(await self._get_auth_headers()),
        }
        if self._signer is not None:
            headers["X-Signature"] = self._signer.sign_bytes(raw_body)

        req = Request(
            method="POST",
            path="/api/v3/utilisation",
            params={"omsId": self._oms_id},
            headers=headers,
            raw_body=raw_body,
        )
        resp = await transport.request(req)
        body = resp.body
        return SendUtilisationResponse(oms_id=body["omsId"], report_id=body["reportId"])

    async def get_report_status(self, report_id: str) -> ReportStatusResponse:
        """Get report processing status (GET /api/v3/report/info)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        req = Request(
            method="GET",
            path="/api/v3/report/info",
            params={"omsId": self._oms_id, "reportId": report_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body = resp.body
        return ReportStatusResponse(
            oms_id=body["omsId"],
            report_id=body["reportId"],
            report_status=body["reportStatus"],
            error_reason=body.get("errorReason"),
        )

    async def get_receipt(self, result_doc_id: str) -> list[dict[str, Any]]:
        """Get receipts by document ID (GET /api/v3/receipts/receipt)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        req = Request(
            method="GET",
            path="/api/v3/receipts/receipt",
            params={"omsId": self._oms_id, "resultDocId": result_doc_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        return cast(list[dict[str, Any]], resp.body["results"])

    async def search_receipts(
        self,
        filter: ReceiptFilter,
        limit: int | None = None,
        skip: int | None = None,
    ) -> SearchReceiptsResponse:
        """Search receipts by filters (POST /api/v3/receipts/receipt/search)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        filter_dict = ReportsApi._filter_to_dict(filter)
        body_dict: dict[str, Any] = {"filter": filter_dict}
        if limit is not None:
            body_dict["limit"] = limit
        if skip is not None:
            body_dict["skip"] = skip

        raw_body = json.dumps(body_dict, ensure_ascii=False).encode()

        req = Request(
            method="POST",
            path="/api/v3/receipts/receipt/search",
            params={"omsId": self._oms_id},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
            raw_body=raw_body,
        )
        resp = await transport.request(req)
        body = resp.body
        return SearchReceiptsResponse(total_count=body["totalCount"], results=body["results"])

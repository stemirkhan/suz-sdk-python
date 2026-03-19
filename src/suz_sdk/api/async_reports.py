"""Async ReportsApi — utilisation reports and receipts (§4.4.11–§4.4.19)."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

from suz_sdk.api.reports import (
    AggregationUnit,
    ReceiptFilter,
    ReportsApi,
    ReportStatusResponse,
    SearchReceiptsResponse,
    SendAggregationResponse,
    SendDropoutResponse,
    SendSurplusResponse,
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

    async def send_dropout(
        self,
        product_group: str,
        sntins: list[str],
        dropout_reason: str,
        attributes: dict[str, Any] | None = None,
    ) -> SendDropoutResponse:
        """Send a KM dropout report (POST /api/v3/dropout)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, Any] = {
            "productGroup": product_group,
            "sntins": sntins,
            "dropoutReason": dropout_reason,
        }
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
            path="/api/v3/dropout",
            params={"omsId": self._oms_id},
            headers=headers,
            raw_body=raw_body,
        )
        resp = await transport.request(req)
        body = resp.body
        return SendDropoutResponse(oms_id=body["omsId"], report_id=body["reportId"])

    async def send_aggregation(
        self,
        product_group: str,
        participant_id: str,
        aggregation_units: list[AggregationUnit],
        attributes: dict[str, Any] | None = None,
    ) -> SendAggregationResponse:
        """Send a KM aggregation report (POST /api/v3/aggregation)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, Any] = {
            "productGroup": product_group,
            "participantId": participant_id,
            "aggregationUnits": [
                {
                    "aggregatedItemsCount": u.aggregated_items_count,
                    "aggregationType": "AGGREGATION",
                    "aggregationUnitCapacity": u.aggregation_unit_capacity,
                    "sntins": u.sntins,
                    "unitSerialNumber": u.unit_serial_number,
                }
                for u in aggregation_units
            ],
        }
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
            path="/api/v3/aggregation",
            params={"omsId": self._oms_id},
            headers=headers,
            raw_body=raw_body,
        )
        resp = await transport.request(req)
        body = resp.body
        return SendAggregationResponse(oms_id=body["omsId"], report_id=body["reportId"])

    async def send_surplus(
        self,
        product_group: str,
        document_date: str,
        participant_inn: str,
        primary_document_custom_name: str,
        primary_document_date: str,
        primary_document_number: str,
        codes: list[str],
        document_type: str = "SURPLUS_POSTING",
        document_version: str = "1.0",
        participant_kpp: str | None = None,
        participant_fias: str | None = None,
    ) -> SendSurplusResponse:
        """Send a surplus posting notification (POST /api/v3/surplus, §4.4.12)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, Any] = {
            "documentType": document_type,
            "documentVersion": document_version,
            "documentDate": document_date,
            "participantInn": participant_inn,
            "primaryDocumentCustomName": primary_document_custom_name,
            "primaryDocumentDate": primary_document_date,
            "primaryDocumentNumber": primary_document_number,
            "codes": codes,
        }
        if participant_kpp is not None:
            body_dict["participantKpp"] = participant_kpp
        if participant_fias is not None:
            body_dict["participantFias"] = participant_fias

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
            path="/api/v3/surplus",
            params={"omsId": self._oms_id, "productGroup": product_group},
            headers=headers,
            raw_body=raw_body,
        )
        resp = await transport.request(req)
        body = resp.body
        return SendSurplusResponse(oms_id=body["omsId"], report_id=body["reportId"])

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

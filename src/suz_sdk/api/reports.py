"""ReportsApi — KM utilisation reports and receipts (§4.4.11, §4.4.13, §4.4.18, §4.4.19).

Endpoints implemented:
    send_utilisation()   POST /api/v3/utilisation          §4.4.11
    get_report_status()  GET  /api/v3/report/info          §4.4.13
    get_receipt()        GET  /api/v3/receipts/receipt     §4.4.18
    search_receipts()    POST /api/v3/receipts/receipt/search §4.4.19

Typical flow:
    1. report = client.reports.send_utilisation(product_group="milk", sntins=[...])
    2. Poll client.reports.get_report_status(report.report_id) until
       report_status == "SUCCESS" or "REJECTED".
    3. Optionally: client.reports.get_receipt(report.report_id)
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import BaseTransport, Request

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


@dataclass
class SendUtilisationResponse:
    """Response from POST /api/v3/utilisation (§4.4.11.2)."""

    oms_id: str
    report_id: str


@dataclass
class ReportStatusResponse:
    """Response from GET /api/v3/report/info (§4.4.13.2)."""

    oms_id: str
    report_id: str
    report_status: str          # SUCCESS | REJECTED | (pending states)
    error_reason: str | None = None


# ---------------------------------------------------------------------------
# Receipt search filter
# ---------------------------------------------------------------------------


@dataclass
class ReceiptFilter:
    """Filter parameters for search_receipts() (§4.4.19, Table 208).

    At least one field must be set.  Date ranges use Unix milliseconds.
    The gap between start and end dates must not exceed 7 calendar days.
    """

    start_create_doc_date: int | None = None
    end_create_doc_date: int | None = None
    start_start_doc_date: int | None = None
    end_start_doc_date: int | None = None
    result_doc_ids: list[str] | None = None      # max 100 elements
    source_doc_ids: list[str] | None = None      # max 100 elements
    order_ids: list[str] | None = None           # max 100 elements
    service_provider_ids: list[str] | None = None  # max 100 elements
    result_codes: list[int] | None = None
    product_groups: list[str] | None = None
    workflow_types: list[str] | None = None      # CREATE_ORDER, GET_CODES, CLOSE_ORDER,
                                                  # ANNULMENT_CODES, REPORT_UTILIZE,
                                                  # REPORT_AGGREGATION, REPORT_DROPOUT,
                                                  # REPORT_QUALITY
    production_order_ids: list[str] | None = None  # max 100 elements


@dataclass
class SearchReceiptsResponse:
    """Response from POST /api/v3/receipts/receipt/search (§4.4.19.3, Table 209)."""

    total_count: int
    results: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# API class
# ---------------------------------------------------------------------------


class ReportsApi:
    """Client for KM utilisation reports and receipt queries (§4.4.11–§4.4.19).

    Args:
        transport:        HTTP transport.
        oms_id:           СУЗ instance UUID (injected as omsId query param).
        get_auth_headers: Callable that returns current auth headers (clientToken).
        signer:           Optional signer for X-Signature header.
                          Required for send_utilisation() on all TGs except
                          pharmaceuticals.
    """

    def __init__(
        self,
        transport: BaseTransport,
        oms_id: str,
        get_auth_headers: Callable[[], dict[str, str]],
        signer: BaseSigner | None = None,
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers
        self._signer = signer

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def send_utilisation(
        self,
        product_group: str,
        sntins: list[str],
        utilisation_type: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> SendUtilisationResponse:
        """Send a KM utilisation (marking/нанесение) report.

        POST /api/v3/utilisation?omsId={omsId}

        The body is JSON-serialised, signed (X-Signature, detached CMS Base64)
        when a signer is provided, then sent verbatim so the signature covers
        the exact bytes on the wire.

        Args:
            product_group:    Product group code (e.g. "milk", "shoes").
            sntins:           List of full KM codes including verification code.
                              Maximum 30 000 elements per request.
            utilisation_type: Optional.  Defaults to "UTILISATION" on the server.
                              Other values: "RESORT", "SPLITMARK", "DIVISIONMARK".
            attributes:       Optional product-group-specific attributes dict.

        Returns:
            SendUtilisationResponse with oms_id and report_id.
        """
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
            **self._get_auth_headers(),
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
        resp = self._transport.request(req)
        body = resp.body
        return SendUtilisationResponse(
            oms_id=body["omsId"],
            report_id=body["reportId"],
        )

    def get_report_status(self, report_id: str) -> ReportStatusResponse:
        """Get the processing status of a utilisation report.

        GET /api/v3/report/info?omsId={omsId}&reportId={reportId}

        Poll until report_status reaches a terminal state (SUCCESS or REJECTED).
        A REJECTED status means the report was declined; check error_reason.

        Args:
            report_id: UUID returned by send_utilisation().

        Returns:
            ReportStatusResponse with report_status and optional error_reason.
        """
        req = Request(
            method="GET",
            path="/api/v3/report/info",
            params={
                "omsId": self._oms_id,
                "reportId": report_id,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body = resp.body
        return ReportStatusResponse(
            oms_id=body["omsId"],
            report_id=body["reportId"],
            report_status=body["reportStatus"],
            error_reason=body.get("errorReason"),
        )

    def get_receipt(self, result_doc_id: str) -> list[dict[str, Any]]:
        """Get receipts by document ID (order ID, report ID, or KM block ID).

        GET /api/v3/receipts/receipt?omsId={omsId}&resultDocId={resultDocId}

        Works only for receipts created under Квитирование 2.0.

        Args:
            result_doc_id: UUID of the document (order, report, or KM block).

        Returns:
            List of receipt dicts.  Structure is described in Section 10 of
            the API spec; the raw dict is returned to avoid loss of detail
            for product-group-specific fields.
        """
        req = Request(
            method="GET",
            path="/api/v3/receipts/receipt",
            params={
                "omsId": self._oms_id,
                "resultDocId": result_doc_id,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        return cast(list[dict[str, Any]], resp.body["results"])

    def search_receipts(
        self,
        filter: ReceiptFilter,
        limit: int | None = None,
        skip: int | None = None,
    ) -> SearchReceiptsResponse:
        """Search receipts by filters.

        POST /api/v3/receipts/receipt/search?omsId={omsId}

        Works only for receipts created under Квитирование 2.0.
        Returns at most 100 records per call.  Use skip for pagination.
        If a date range filter is used, the gap between start and end must
        not exceed 7 calendar days.

        Args:
            filter: ReceiptFilter with at least one field set.
            limit:  Max records to return (default 10, max 100).
            skip:   Page offset (default 1).

        Returns:
            SearchReceiptsResponse with total_count and results list.
        """
        filter_dict = self._filter_to_dict(filter)
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
                **self._get_auth_headers(),
            },
            raw_body=raw_body,
        )
        resp = self._transport.request(req)
        body = resp.body
        return SearchReceiptsResponse(
            total_count=body["totalCount"],
            results=body["results"],
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_to_dict(f: ReceiptFilter) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if f.start_create_doc_date is not None:
            d["startCreateDocDate"] = f.start_create_doc_date
        if f.end_create_doc_date is not None:
            d["endCreateDocDate"] = f.end_create_doc_date
        if f.start_start_doc_date is not None:
            d["startStartDocDate"] = f.start_start_doc_date
        if f.end_start_doc_date is not None:
            d["endStartDocDate"] = f.end_start_doc_date
        if f.result_doc_ids is not None:
            d["resultDocIds"] = f.result_doc_ids
        if f.source_doc_ids is not None:
            d["sourceDocIds"] = f.source_doc_ids
        if f.order_ids is not None:
            d["orderIds"] = f.order_ids
        if f.service_provider_ids is not None:
            d["serviceProviderIds"] = f.service_provider_ids
        if f.result_codes is not None:
            d["resultCodes"] = f.result_codes
        if f.product_groups is not None:
            d["productGroups"] = f.product_groups
        if f.workflow_types is not None:
            d["workflowTypes"] = f.workflow_types
        if f.production_order_ids is not None:
            d["productionOrderIds"] = f.production_order_ids
        return d

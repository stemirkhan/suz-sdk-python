"""Unit tests for ReportsApi (§4.4.11, §4.4.13, §4.4.18, §4.4.19)."""

import json

import pytest

from suz_sdk.api.reports import (
    ReceiptFilter,
    ReportStatusResponse,
    ReportsApi,
    SearchReceiptsResponse,
    SendUtilisationResponse,
)
from suz_sdk.signing.noop import NoopSigner
from suz_sdk.transport.base import Request, Response


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

OMS_ID = "aaaaaaaa-0000-0000-0000-000000000000"
REPORT_ID = "bbbbbbbb-1111-1111-1111-111111111111"
DOC_ID = "cccccccc-2222-2222-2222-222222222222"


class CapturingTransport:
    """Records the last request and returns a pre-configured response."""

    def __init__(self, response_body: object) -> None:
        self.response_body = response_body
        self.last_request: Request | None = None

    def request(self, req: Request) -> Response:
        self.last_request = req
        return Response(status_code=200, headers={}, body=self.response_body)


def make_api(transport, signer=None):
    return ReportsApi(
        transport=transport,
        oms_id=OMS_ID,
        get_auth_headers=lambda: {"clientToken": "tok"},
        signer=signer,
    )


# ---------------------------------------------------------------------------
# send_utilisation
# ---------------------------------------------------------------------------


class TestSendUtilisation:
    def test_returns_response(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        api = make_api(transport)
        resp = api.send_utilisation(
            product_group="milk",
            sntins=["010460200640730421CM7SJdpPjHqkF"],
        )
        assert isinstance(resp, SendUtilisationResponse)
        assert resp.oms_id == OMS_ID
        assert resp.report_id == REPORT_ID

    def test_request_method_and_path(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["sntin1"])
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/utilisation"

    def test_oms_id_in_params(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["sntin1"])
        assert transport.last_request.params["omsId"] == OMS_ID

    def test_body_contains_product_group_and_sntins(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        sntins = ["code1", "code2"]
        make_api(transport).send_utilisation("shoes", sntins)
        body = json.loads(transport.last_request.raw_body)
        assert body["productGroup"] == "shoes"
        assert body["sntins"] == sntins

    def test_optional_utilisation_type(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["s1"], utilisation_type="RESORT")
        body = json.loads(transport.last_request.raw_body)
        assert body["utilisationType"] == "RESORT"

    def test_utilisation_type_omitted_when_none(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["s1"])
        body = json.loads(transport.last_request.raw_body)
        assert "utilisationType" not in body

    def test_optional_attributes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        attrs = {"key": "value"}
        make_api(transport).send_utilisation("milk", ["s1"], attributes=attrs)
        body = json.loads(transport.last_request.raw_body)
        assert body["attributes"] == attrs

    def test_attributes_omitted_when_none(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["s1"])
        body = json.loads(transport.last_request.raw_body)
        assert "attributes" not in body

    def test_content_type_header(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["s1"])
        assert transport.last_request.headers["Content-Type"] == "application/json"

    def test_auth_header_injected(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["s1"])
        assert transport.last_request.headers["clientToken"] == "tok"

    def test_signature_header_when_signer_present(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        make_api(transport, signer=signer).send_utilisation("milk", ["s1"])
        assert "X-Signature" in transport.last_request.headers

    def test_no_signature_header_without_signer(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["s1"])
        assert "X-Signature" not in transport.last_request.headers

    def test_signature_covers_raw_body(self):
        """NoopSigner returns hex of raw_body; signature must match body bytes."""
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        make_api(transport, signer=signer).send_utilisation("milk", ["s1"])
        req = transport.last_request
        expected = signer.sign_bytes(req.raw_body)
        assert req.headers["X-Signature"] == expected

    def test_raw_body_is_bytes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_utilisation("milk", ["s1"])
        assert isinstance(transport.last_request.raw_body, bytes)

    def test_multiple_sntins(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        sntins = [f"code{i}" for i in range(100)]
        make_api(transport).send_utilisation("tobacco", sntins)
        body = json.loads(transport.last_request.raw_body)
        assert len(body["sntins"]) == 100


# ---------------------------------------------------------------------------
# get_report_status
# ---------------------------------------------------------------------------


class TestGetReportStatus:
    def _success_body(self, status="SUCCESS", error_reason=None):
        d = {"omsId": OMS_ID, "reportId": REPORT_ID, "reportStatus": status}
        if error_reason is not None:
            d["errorReason"] = error_reason
        return d

    def test_returns_response(self):
        transport = CapturingTransport(self._success_body())
        resp = make_api(transport).get_report_status(REPORT_ID)
        assert isinstance(resp, ReportStatusResponse)
        assert resp.report_status == "SUCCESS"
        assert resp.report_id == REPORT_ID
        assert resp.oms_id == OMS_ID

    def test_request_method_and_path(self):
        transport = CapturingTransport(self._success_body())
        make_api(transport).get_report_status(REPORT_ID)
        req = transport.last_request
        assert req.method == "GET"
        assert req.path == "/api/v3/report/info"

    def test_params_contain_oms_id_and_report_id(self):
        transport = CapturingTransport(self._success_body())
        make_api(transport).get_report_status(REPORT_ID)
        params = transport.last_request.params
        assert params["omsId"] == OMS_ID
        assert params["reportId"] == REPORT_ID

    def test_auth_header_injected(self):
        transport = CapturingTransport(self._success_body())
        make_api(transport).get_report_status(REPORT_ID)
        assert transport.last_request.headers["clientToken"] == "tok"

    def test_error_reason_when_rejected(self):
        transport = CapturingTransport(
            self._success_body("REJECTED", "Invalid KM code")
        )
        resp = make_api(transport).get_report_status(REPORT_ID)
        assert resp.report_status == "REJECTED"
        assert resp.error_reason == "Invalid KM code"

    def test_error_reason_none_when_success(self):
        transport = CapturingTransport(self._success_body("SUCCESS"))
        resp = make_api(transport).get_report_status(REPORT_ID)
        assert resp.error_reason is None

    def test_no_body_sent(self):
        transport = CapturingTransport(self._success_body())
        make_api(transport).get_report_status(REPORT_ID)
        assert transport.last_request.raw_body is None


# ---------------------------------------------------------------------------
# get_receipt
# ---------------------------------------------------------------------------


SAMPLE_RECEIPT = {
    "resultDocId": DOC_ID,
    "resultDocDate": 1633441943252,
    "sourceDocId": "source-id",
    "sourceDocDate": 1633441923090,
    "state": "SUCCESS",
    "code": 0,
    "description": "Document was successfully processed",
    "workflow": "REPORT_UTILIZE",
    "workflowVersion": 1,
    "details": {},
    "operations": [],
}


class TestGetReceipt:
    def test_returns_list(self):
        transport = CapturingTransport({"results": [SAMPLE_RECEIPT]})
        result = make_api(transport).get_receipt(DOC_ID)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["resultDocId"] == DOC_ID

    def test_request_method_and_path(self):
        transport = CapturingTransport({"results": []})
        make_api(transport).get_receipt(DOC_ID)
        req = transport.last_request
        assert req.method == "GET"
        assert req.path == "/api/v3/receipts/receipt"

    def test_params(self):
        transport = CapturingTransport({"results": []})
        make_api(transport).get_receipt(DOC_ID)
        params = transport.last_request.params
        assert params["omsId"] == OMS_ID
        assert params["resultDocId"] == DOC_ID

    def test_auth_header_injected(self):
        transport = CapturingTransport({"results": []})
        make_api(transport).get_receipt(DOC_ID)
        assert transport.last_request.headers["clientToken"] == "tok"

    def test_empty_results(self):
        transport = CapturingTransport({"results": []})
        result = make_api(transport).get_receipt(DOC_ID)
        assert result == []

    def test_multiple_receipts(self):
        receipts = [dict(SAMPLE_RECEIPT, resultDocId=f"id-{i}") for i in range(3)]
        transport = CapturingTransport({"results": receipts})
        result = make_api(transport).get_receipt(DOC_ID)
        assert len(result) == 3

    def test_no_body_sent(self):
        transport = CapturingTransport({"results": []})
        make_api(transport).get_receipt(DOC_ID)
        assert transport.last_request.raw_body is None


# ---------------------------------------------------------------------------
# search_receipts
# ---------------------------------------------------------------------------


class TestSearchReceipts:
    def _make_response(self, results=None, total_count=0):
        return {"totalCount": total_count, "results": results or []}

    def test_returns_response(self):
        transport = CapturingTransport(
            self._make_response([SAMPLE_RECEIPT], total_count=1)
        )
        f = ReceiptFilter(order_ids=["order-1"])
        resp = make_api(transport).search_receipts(f)
        assert isinstance(resp, SearchReceiptsResponse)
        assert resp.total_count == 1
        assert len(resp.results) == 1

    def test_request_method_and_path(self):
        transport = CapturingTransport(self._make_response())
        make_api(transport).search_receipts(ReceiptFilter(order_ids=["x"]))
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/receipts/receipt/search"

    def test_oms_id_in_params(self):
        transport = CapturingTransport(self._make_response())
        make_api(transport).search_receipts(ReceiptFilter(order_ids=["x"]))
        assert transport.last_request.params["omsId"] == OMS_ID

    def test_filter_serialised_in_body(self):
        transport = CapturingTransport(self._make_response())
        f = ReceiptFilter(order_ids=["order-abc"], product_groups=["milk"])
        make_api(transport).search_receipts(f)
        body = json.loads(transport.last_request.raw_body)
        assert body["filter"]["orderIds"] == ["order-abc"]
        assert body["filter"]["productGroups"] == ["milk"]

    def test_limit_and_skip_in_body(self):
        transport = CapturingTransport(self._make_response())
        make_api(transport).search_receipts(
            ReceiptFilter(order_ids=["x"]), limit=50, skip=2
        )
        body = json.loads(transport.last_request.raw_body)
        assert body["limit"] == 50
        assert body["skip"] == 2

    def test_limit_and_skip_omitted_when_none(self):
        transport = CapturingTransport(self._make_response())
        make_api(transport).search_receipts(ReceiptFilter(order_ids=["x"]))
        body = json.loads(transport.last_request.raw_body)
        assert "limit" not in body
        assert "skip" not in body

    def test_auth_header_injected(self):
        transport = CapturingTransport(self._make_response())
        make_api(transport).search_receipts(ReceiptFilter(order_ids=["x"]))
        assert transport.last_request.headers["clientToken"] == "tok"

    def test_content_type_header(self):
        transport = CapturingTransport(self._make_response())
        make_api(transport).search_receipts(ReceiptFilter(order_ids=["x"]))
        assert transport.last_request.headers["Content-Type"] == "application/json"

    def test_raw_body_is_bytes(self):
        transport = CapturingTransport(self._make_response())
        make_api(transport).search_receipts(ReceiptFilter(order_ids=["x"]))
        assert isinstance(transport.last_request.raw_body, bytes)

    def test_empty_results(self):
        transport = CapturingTransport(self._make_response([], 0))
        resp = make_api(transport).search_receipts(ReceiptFilter(order_ids=["x"]))
        assert resp.total_count == 0
        assert resp.results == []


# ---------------------------------------------------------------------------
# ReceiptFilter serialisation
# ---------------------------------------------------------------------------


class TestReceiptFilterToDict:
    def test_empty_filter_produces_empty_dict(self):
        d = ReportsApi._filter_to_dict(ReceiptFilter())
        assert d == {}

    def test_all_fields_serialised(self):
        f = ReceiptFilter(
            start_create_doc_date=1000,
            end_create_doc_date=2000,
            start_start_doc_date=3000,
            end_start_doc_date=4000,
            result_doc_ids=["r1"],
            source_doc_ids=["s1"],
            order_ids=["o1"],
            service_provider_ids=["sp1"],
            result_codes=[0, 1],
            product_groups=["milk"],
            workflow_types=["REPORT_UTILIZE"],
            production_order_ids=["po1"],
        )
        d = ReportsApi._filter_to_dict(f)
        assert d["startCreateDocDate"] == 1000
        assert d["endCreateDocDate"] == 2000
        assert d["startStartDocDate"] == 3000
        assert d["endStartDocDate"] == 4000
        assert d["resultDocIds"] == ["r1"]
        assert d["sourceDocIds"] == ["s1"]
        assert d["orderIds"] == ["o1"]
        assert d["serviceProviderIds"] == ["sp1"]
        assert d["resultCodes"] == [0, 1]
        assert d["productGroups"] == ["milk"]
        assert d["workflowTypes"] == ["REPORT_UTILIZE"]
        assert d["productionOrderIds"] == ["po1"]

    def test_none_fields_excluded(self):
        f = ReceiptFilter(order_ids=["o1"])
        d = ReportsApi._filter_to_dict(f)
        assert set(d.keys()) == {"orderIds"}


# ---------------------------------------------------------------------------
# SuzClient wiring
# ---------------------------------------------------------------------------


class TestSuzClientWiring:
    def test_client_has_reports_attribute(self):
        from suz_sdk import SuzClient
        from suz_sdk.transport.base import Response

        class FakeTransport:
            def request(self, req):
                return Response(status_code=200, headers={}, body={"omsId": OMS_ID, "apiVersion": "3", "omsVersion": "4"})

        client = SuzClient(
            oms_id=OMS_ID,
            client_token="tok",
            transport=FakeTransport(),
        )
        assert hasattr(client, "reports")
        assert isinstance(client.reports, ReportsApi)

    def test_reports_shares_oms_id(self):
        from suz_sdk import SuzClient
        from suz_sdk.transport.base import Response

        class FakeTransport:
            def request(self, req):
                return Response(status_code=200, headers={}, body={})

        client = SuzClient(
            oms_id=OMS_ID,
            client_token="tok",
            transport=FakeTransport(),
        )
        assert client.reports._oms_id == OMS_ID

    def test_reports_signer_wired(self):
        from suz_sdk import SuzClient
        from suz_sdk.transport.base import Response

        class FakeTransport:
            def request(self, req):
                return Response(status_code=200, headers={}, body={})

        signer = NoopSigner()
        client = SuzClient(
            oms_id=OMS_ID,
            client_token="tok",
            signer=signer,
            transport=FakeTransport(),
        )
        assert client.reports._signer is signer

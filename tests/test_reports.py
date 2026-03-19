"""Unit tests for ReportsApi (§4.4.11, §4.4.13, §4.4.18, §4.4.19)."""

import json

import pytest

from suz_sdk.api.async_reports import AsyncReportsApi
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
from suz_sdk.signing.noop import NoopSigner
from suz_sdk.transport.base import Request, Response  # noqa: F401

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

OMS_ID = "aaaaaaaa-0000-0000-0000-000000000000"
REPORT_ID = "bbbbbbbb-1111-1111-1111-111111111111"
DOC_ID = "cccccccc-2222-2222-2222-222222222222"

_SURPLUS_DATE = "2022-03-11T05:10:00.872791Z"
_SURPLUS_INN = "7825706086"
_SURPLUS_CODES = ["000000462095287,b4*i%93dGVz"]


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
                return Response(
                    status_code=200,
                    headers={},
                    body={"omsId": OMS_ID, "apiVersion": "3", "omsVersion": "4"},
                )

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


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


class AsyncCapturingTransport:
    """Records the last request and returns a pre-configured async response."""

    def __init__(self, response_body: object) -> None:
        self.response_body = response_body
        self.last_request: Request | None = None

    async def request(self, req: Request) -> Response:
        self.last_request = req
        return Response(status_code=200, headers={}, body=self.response_body)

    async def aclose(self) -> None:
        pass


def make_async_api(transport, signer=None):
    return AsyncReportsApi(
        transport=transport,
        oms_id=OMS_ID,
        get_auth_headers=lambda: _async_auth_headers(),
        signer=signer,
    )


async def _async_auth_headers() -> dict:
    return {"clientToken": "tok"}


# ---------------------------------------------------------------------------
# send_dropout (sync)
# ---------------------------------------------------------------------------


class TestSendDropout:
    def test_returns_response(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        api = make_api(transport)
        resp = api.send_dropout(
            product_group="milk",
            sntins=["010460200640730421CM7SJdpPjHqkF"],
            dropout_reason="DEFECT",
        )
        assert isinstance(resp, SendDropoutResponse)
        assert resp.oms_id == OMS_ID
        assert resp.report_id == REPORT_ID

    def test_request_method_and_path(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["sntin1"], "DEFECT")
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/dropout"

    def test_oms_id_in_params(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["sntin1"], "DEFECT")
        assert transport.last_request.params["omsId"] == OMS_ID

    def test_body_contains_product_group_and_sntins(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        sntins = ["code1", "code2"]
        make_api(transport).send_dropout("shoes", sntins, "DEFECT")
        body = json.loads(transport.last_request.raw_body)
        assert body["productGroup"] == "shoes"
        assert body["sntins"] == sntins

    def test_dropout_reason_in_body(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["s1"], dropout_reason="DEFECT")
        body = json.loads(transport.last_request.raw_body)
        assert body["dropoutReason"] == "DEFECT"

    def test_optional_attributes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        attrs = {"key": "value"}
        make_api(transport).send_dropout("milk", ["s1"], "DEFECT", attributes=attrs)
        body = json.loads(transport.last_request.raw_body)
        assert body["attributes"] == attrs

    def test_attributes_omitted_when_none(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        body = json.loads(transport.last_request.raw_body)
        assert "attributes" not in body

    def test_content_type_header(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        assert transport.last_request.headers["Content-Type"] == "application/json"

    def test_auth_header_injected(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        assert transport.last_request.headers["clientToken"] == "tok"

    def test_signature_header_when_signer_present(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        make_api(transport, signer=signer).send_dropout("milk", ["s1"], "DEFECT")
        assert "X-Signature" in transport.last_request.headers

    def test_no_signature_header_without_signer(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        assert "X-Signature" not in transport.last_request.headers

    def test_signature_covers_raw_body(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        make_api(transport, signer=signer).send_dropout("milk", ["s1"], "DEFECT")
        req = transport.last_request
        expected = signer.sign_bytes(req.raw_body)
        assert req.headers["X-Signature"] == expected

    def test_raw_body_is_bytes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        make_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        assert isinstance(transport.last_request.raw_body, bytes)


# ---------------------------------------------------------------------------
# send_aggregation (sync)
# ---------------------------------------------------------------------------

_AGG_INN = "1234567890"
_AGG_UNIT = AggregationUnit(
    sntins=["010460200640730421CM7SJdpPjHqkF"],
    unit_serial_number="010460200640730421",
    aggregated_items_count=1,
    aggregation_unit_capacity=1,
)


def _make_aggregation_call(api, product_group="milk", participant_id=_AGG_INN,
                           aggregation_units=None, **kwargs):
    if aggregation_units is None:
        aggregation_units = [_AGG_UNIT]
    return api.send_aggregation(
        product_group=product_group,
        participant_id=participant_id,
        aggregation_units=aggregation_units,
        **kwargs,
    )


class TestSendAggregation:
    def test_returns_response(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        resp = _make_aggregation_call(make_api(transport))
        assert isinstance(resp, SendAggregationResponse)
        assert resp.oms_id == OMS_ID
        assert resp.report_id == REPORT_ID

    def test_request_method_and_path(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(make_api(transport))
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/aggregation"

    def test_oms_id_in_params(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(make_api(transport))
        assert transport.last_request.params["omsId"] == OMS_ID

    def test_body_contains_product_group_and_participant_id(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(
            make_api(transport), product_group="shoes", participant_id="9876543210"
        )
        body = json.loads(transport.last_request.raw_body)
        assert body["productGroup"] == "shoes"
        assert body["participantId"] == "9876543210"

    def test_body_contains_aggregation_units(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        unit = AggregationUnit(
            sntins=["code1", "code2"],
            unit_serial_number="UNIT001",
            aggregated_items_count=2,
            aggregation_unit_capacity=10,
        )
        _make_aggregation_call(make_api(transport), aggregation_units=[unit])
        body = json.loads(transport.last_request.raw_body)
        assert len(body["aggregationUnits"]) == 1
        u = body["aggregationUnits"][0]
        assert u["sntins"] == ["code1", "code2"]
        assert u["unitSerialNumber"] == "UNIT001"
        assert u["aggregatedItemsCount"] == 2
        assert u["aggregationUnitCapacity"] == 10
        assert u["aggregationType"] == "AGGREGATION"

    def test_optional_attributes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        attrs = {"productionLineId": "LINE1"}
        _make_aggregation_call(make_api(transport), attributes=attrs)
        body = json.loads(transport.last_request.raw_body)
        assert body["attributes"] == attrs

    def test_attributes_omitted_when_none(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(make_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert "attributes" not in body

    def test_content_type_header(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(make_api(transport))
        assert transport.last_request.headers["Content-Type"] == "application/json"

    def test_auth_header_injected(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(make_api(transport))
        assert transport.last_request.headers["clientToken"] == "tok"

    def test_signature_header_when_signer_present(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        _make_aggregation_call(make_api(transport, signer=signer))
        assert "X-Signature" in transport.last_request.headers

    def test_no_signature_header_without_signer(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(make_api(transport))
        assert "X-Signature" not in transport.last_request.headers

    def test_signature_covers_raw_body(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        _make_aggregation_call(make_api(transport, signer=signer))
        req = transport.last_request
        expected = signer.sign_bytes(req.raw_body)
        assert req.headers["X-Signature"] == expected

    def test_raw_body_is_bytes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_aggregation_call(make_api(transport))
        assert isinstance(transport.last_request.raw_body, bytes)


# ---------------------------------------------------------------------------
# send_surplus (sync)
# ---------------------------------------------------------------------------


def _make_surplus_call(api, product_group="milk", **kwargs):
    """Helper: call send_surplus with all required args."""
    return api.send_surplus(
        product_group=product_group,
        document_date=_SURPLUS_DATE,
        participant_inn=_SURPLUS_INN,
        primary_document_custom_name="Излишки",
        primary_document_date=_SURPLUS_DATE,
        primary_document_number="ИЗЛ-001",
        codes=_SURPLUS_CODES,
        **kwargs,
    )


class TestSendSurplus:
    def test_returns_response(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        api = make_api(transport)
        resp = _make_surplus_call(api)
        assert isinstance(resp, SendSurplusResponse)
        assert resp.oms_id == OMS_ID
        assert resp.report_id == REPORT_ID

    def test_request_method_and_path(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/surplus"

    def test_oms_id_in_params(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        assert transport.last_request.params["omsId"] == OMS_ID

    def test_product_group_in_params(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport), product_group="milk")
        assert transport.last_request.params["productGroup"] == "milk"

    def test_body_contains_document_type(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["documentType"] == "SURPLUS_POSTING"

    def test_body_contains_document_version(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["documentVersion"] == "1.0"

    def test_body_contains_document_date(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["documentDate"] == _SURPLUS_DATE

    def test_body_contains_participant_inn(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["participantInn"] == _SURPLUS_INN

    def test_body_contains_codes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["codes"] == _SURPLUS_CODES

    def test_optional_participant_kpp(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport), participant_kpp="783901001")
        body = json.loads(transport.last_request.raw_body)
        assert body["participantKpp"] == "783901001"

    def test_participant_kpp_omitted_when_none(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert "participantKpp" not in body

    def test_optional_participant_fias(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport), participant_fias="some-guid")
        body = json.loads(transport.last_request.raw_body)
        assert body["participantFias"] == "some-guid"

    def test_content_type_header(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        assert transport.last_request.headers["Content-Type"] == "application/json"

    def test_auth_header_injected(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        assert transport.last_request.headers["clientToken"] == "tok"

    def test_signature_header_when_signer_present(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        _make_surplus_call(make_api(transport, signer=signer))
        assert "X-Signature" in transport.last_request.headers

    def test_no_signature_header_without_signer(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        assert "X-Signature" not in transport.last_request.headers

    def test_signature_covers_raw_body(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        _make_surplus_call(make_api(transport, signer=signer))
        req = transport.last_request
        expected = signer.sign_bytes(req.raw_body)
        assert req.headers["X-Signature"] == expected

    def test_raw_body_is_bytes(self):
        transport = CapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        _make_surplus_call(make_api(transport))
        assert isinstance(transport.last_request.raw_body, bytes)


# ---------------------------------------------------------------------------
# send_dropout (async)
# ---------------------------------------------------------------------------


class TestAsyncSendDropout:
    @pytest.mark.anyio
    async def test_returns_response(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        api = make_async_api(transport)
        resp = await api.send_dropout(product_group="milk", sntins=["s1"], dropout_reason="DEFECT")
        assert isinstance(resp, SendDropoutResponse)
        assert resp.oms_id == OMS_ID
        assert resp.report_id == REPORT_ID

    @pytest.mark.anyio
    async def test_request_method_and_path(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await make_async_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/dropout"

    @pytest.mark.anyio
    async def test_oms_id_in_params(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await make_async_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        assert transport.last_request.params["omsId"] == OMS_ID

    @pytest.mark.anyio
    async def test_body_contains_product_group_and_sntins(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        sntins = ["code1", "code2"]
        await make_async_api(transport).send_dropout("shoes", sntins, "DEFECT")
        body = json.loads(transport.last_request.raw_body)
        assert body["productGroup"] == "shoes"
        assert body["sntins"] == sntins

    @pytest.mark.anyio
    async def test_dropout_reason_in_body(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await make_async_api(transport).send_dropout("milk", ["s1"], dropout_reason="DEFECT")
        body = json.loads(transport.last_request.raw_body)
        assert body["dropoutReason"] == "DEFECT"

    @pytest.mark.anyio
    async def test_signature_header_when_signer_present(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        await make_async_api(transport, signer=signer).send_dropout("milk", ["s1"], "DEFECT")
        assert "X-Signature" in transport.last_request.headers

    @pytest.mark.anyio
    async def test_no_signature_header_without_signer(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await make_async_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        assert "X-Signature" not in transport.last_request.headers

    @pytest.mark.anyio
    async def test_raw_body_is_bytes(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await make_async_api(transport).send_dropout("milk", ["s1"], "DEFECT")
        assert isinstance(transport.last_request.raw_body, bytes)


# ---------------------------------------------------------------------------
# send_aggregation (async)
# ---------------------------------------------------------------------------


async def _make_async_aggregation_call(api, product_group="milk",
                                       participant_id=_AGG_INN,
                                       aggregation_units=None, **kwargs):
    if aggregation_units is None:
        aggregation_units = [_AGG_UNIT]
    return await api.send_aggregation(
        product_group=product_group,
        participant_id=participant_id,
        aggregation_units=aggregation_units,
        **kwargs,
    )


class TestAsyncSendAggregation:
    @pytest.mark.anyio
    async def test_returns_response(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        resp = await _make_async_aggregation_call(make_async_api(transport))
        assert isinstance(resp, SendAggregationResponse)
        assert resp.oms_id == OMS_ID
        assert resp.report_id == REPORT_ID

    @pytest.mark.anyio
    async def test_request_method_and_path(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_aggregation_call(make_async_api(transport))
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/aggregation"

    @pytest.mark.anyio
    async def test_oms_id_in_params(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_aggregation_call(make_async_api(transport))
        assert transport.last_request.params["omsId"] == OMS_ID

    @pytest.mark.anyio
    async def test_body_contains_product_group_and_participant_id(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_aggregation_call(make_async_api(transport),
                                           product_group="shoes",
                                           participant_id="9876543210")
        body = json.loads(transport.last_request.raw_body)
        assert body["productGroup"] == "shoes"
        assert body["participantId"] == "9876543210"

    @pytest.mark.anyio
    async def test_body_contains_aggregation_units(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        unit = AggregationUnit(
            sntins=["code1", "code2"],
            unit_serial_number="UNIT001",
            aggregated_items_count=2,
            aggregation_unit_capacity=10,
        )
        await _make_async_aggregation_call(make_async_api(transport), aggregation_units=[unit])
        body = json.loads(transport.last_request.raw_body)
        assert len(body["aggregationUnits"]) == 1
        u = body["aggregationUnits"][0]
        assert u["sntins"] == ["code1", "code2"]
        assert u["unitSerialNumber"] == "UNIT001"
        assert u["aggregationType"] == "AGGREGATION"

    @pytest.mark.anyio
    async def test_signature_header_when_signer_present(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        await _make_async_aggregation_call(make_async_api(transport, signer=signer))
        assert "X-Signature" in transport.last_request.headers

    @pytest.mark.anyio
    async def test_no_signature_header_without_signer(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_aggregation_call(make_async_api(transport))
        assert "X-Signature" not in transport.last_request.headers

    @pytest.mark.anyio
    async def test_raw_body_is_bytes(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_aggregation_call(make_async_api(transport))
        assert isinstance(transport.last_request.raw_body, bytes)


# ---------------------------------------------------------------------------
# send_surplus (async)
# ---------------------------------------------------------------------------


async def _make_async_surplus_call(api, product_group="milk", **kwargs):
    """Helper: call async send_surplus with all required args."""
    return await api.send_surplus(
        product_group=product_group,
        document_date=_SURPLUS_DATE,
        participant_inn=_SURPLUS_INN,
        primary_document_custom_name="Излишки",
        primary_document_date=_SURPLUS_DATE,
        primary_document_number="ИЗЛ-001",
        codes=_SURPLUS_CODES,
        **kwargs,
    )


class TestAsyncSendSurplus:
    @pytest.mark.anyio
    async def test_returns_response(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        api = make_async_api(transport)
        resp = await _make_async_surplus_call(api)
        assert isinstance(resp, SendSurplusResponse)
        assert resp.oms_id == OMS_ID
        assert resp.report_id == REPORT_ID

    @pytest.mark.anyio
    async def test_request_method_and_path(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        req = transport.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/surplus"

    @pytest.mark.anyio
    async def test_oms_id_in_params(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        assert transport.last_request.params["omsId"] == OMS_ID

    @pytest.mark.anyio
    async def test_product_group_in_params(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport), product_group="milk")
        assert transport.last_request.params["productGroup"] == "milk"

    @pytest.mark.anyio
    async def test_body_contains_document_type(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["documentType"] == "SURPLUS_POSTING"

    @pytest.mark.anyio
    async def test_body_contains_document_version(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["documentVersion"] == "1.0"

    @pytest.mark.anyio
    async def test_body_contains_document_date(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["documentDate"] == _SURPLUS_DATE

    @pytest.mark.anyio
    async def test_body_contains_participant_inn(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["participantInn"] == _SURPLUS_INN

    @pytest.mark.anyio
    async def test_body_contains_codes(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert body["codes"] == _SURPLUS_CODES

    @pytest.mark.anyio
    async def test_optional_participant_kpp(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport), participant_kpp="783901001")
        body = json.loads(transport.last_request.raw_body)
        assert body["participantKpp"] == "783901001"

    @pytest.mark.anyio
    async def test_participant_kpp_omitted_when_none(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        body = json.loads(transport.last_request.raw_body)
        assert "participantKpp" not in body

    @pytest.mark.anyio
    async def test_optional_participant_fias(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport), participant_fias="some-guid")
        body = json.loads(transport.last_request.raw_body)
        assert body["participantFias"] == "some-guid"

    @pytest.mark.anyio
    async def test_content_type_header(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        assert transport.last_request.headers["Content-Type"] == "application/json"

    @pytest.mark.anyio
    async def test_auth_header_injected(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        assert transport.last_request.headers["clientToken"] == "tok"

    @pytest.mark.anyio
    async def test_signature_header_when_signer_present(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        await _make_async_surplus_call(make_async_api(transport, signer=signer))
        assert "X-Signature" in transport.last_request.headers

    @pytest.mark.anyio
    async def test_no_signature_header_without_signer(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        assert "X-Signature" not in transport.last_request.headers

    @pytest.mark.anyio
    async def test_signature_covers_raw_body(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        signer = NoopSigner()
        await _make_async_surplus_call(make_async_api(transport, signer=signer))
        req = transport.last_request
        expected = signer.sign_bytes(req.raw_body)
        assert req.headers["X-Signature"] == expected

    @pytest.mark.anyio
    async def test_raw_body_is_bytes(self):
        transport = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        await _make_async_surplus_call(make_async_api(transport))
        assert isinstance(transport.last_request.raw_body, bytes)

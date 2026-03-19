"""Tests for DocumentsApi and AsyncDocumentsApi.

Covers:
  - HTTP method and path correctness
  - Query parameter injection (omsId, resultDocId, documentType, docId, limit, skip)
  - Request body for sign_document
  - Response model field mapping
  - Auth header injection
  - SuzClient / AsyncSuzClient wiring
"""

import pytest

from suz_sdk.api.documents import (
    AsyncDocumentsApi,
    DeleteDocumentResponse,
    DocumentsApi,
    SearchDocumentsResponse,
    SignDocumentResponse,
)
from suz_sdk.transport.base import Request, Response

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_OMS_ID = "cdf12109-10d3-11e6-8b6f-0050569977a1"
_TOKEN = "test-client-token"
_RESULT_DOC_ID = "rdoc-0001-0002-0003"
_DOC_ID = "doc-1111-2222-3333"
_DOC_TYPE = "RECEIPT"
_SIGNATURE = "base64signaturehere=="

# ---------------------------------------------------------------------------
# Stub transports
# ---------------------------------------------------------------------------


class StubTransport:
    """Records the last request and returns a preset Response or raises."""

    def __init__(
        self,
        response: Response | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._exc = exc
        self.last_request: Request | None = None

    def request(self, req: Request) -> Response:
        self.last_request = req
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


class AsyncStubTransport:
    """Async version of StubTransport."""

    def __init__(
        self,
        response: Response | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._exc = exc
        self.last_request: Request | None = None

    async def request(self, req: Request) -> Response:
        self.last_request = req
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response

    async def aclose(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api(transport: StubTransport, token: str | None = _TOKEN) -> DocumentsApi:
    def get_auth_headers() -> dict[str, str]:
        return {"clientToken": token} if token else {}

    return DocumentsApi(
        transport=transport,
        oms_id=_OMS_ID,
        get_auth_headers=get_auth_headers,
    )


def _make_async_api(
    transport: AsyncStubTransport, token: str | None = _TOKEN
) -> AsyncDocumentsApi:
    async def get_auth_headers() -> dict[str, str]:
        return {"clientToken": token} if token else {}

    return AsyncDocumentsApi(
        transport=transport,
        oms_id=_OMS_ID,
        get_auth_headers=get_auth_headers,
    )


def _ok(body: object) -> Response:
    return Response(status_code=200, headers={}, body=body)


# ---------------------------------------------------------------------------
# get_receipt_document — sync
# ---------------------------------------------------------------------------


class TestGetReceiptDocument:
    def test_returns_dict(self) -> None:
        payload = {"docId": _RESULT_DOC_ID, "status": "PROCESSED"}
        transport = StubTransport(response=_ok(payload))
        api = _make_api(transport)
        result = api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        assert isinstance(result, dict)
        assert result["docId"] == _RESULT_DOC_ID

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/receipts/document"

    def test_sends_doc_id_in_params(self) -> None:
        transport = StubTransport(response=_ok({"content": "..."}))
        api = _make_api(transport)
        api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("docId") == _DOC_ID

    def test_sends_oms_id_and_result_doc_id(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("resultDocId") == _RESULT_DOC_ID

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport, token=_TOKEN)
        api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_no_token_sends_no_auth_header(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport, token=None)
        api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert "clientToken" not in req.headers

    def test_sends_accept_json_header(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Accept") == "application/json"

    def test_empty_response_returns_empty_dict(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        result = api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        assert result == {}


# ---------------------------------------------------------------------------
# search_documents — sync
# ---------------------------------------------------------------------------


class TestSearchDocuments:
    def test_returns_search_documents_response(self) -> None:
        docs = [{"docId": "d1"}, {"docId": "d2"}]
        transport = StubTransport(response=_ok({"totalCount": 2, "result": docs}))
        api = _make_api(transport)
        result = api.search_documents(_DOC_TYPE)
        assert isinstance(result, SearchDocumentsResponse)
        assert result.total_count == 2
        assert result.results == docs

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_api(transport)
        api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/documents/search"

    def test_sends_oms_id_and_document_type(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_api(transport)
        api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("documentType") == _DOC_TYPE

    def test_sends_optional_limit_and_skip(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_api(transport)
        api.search_documents(_DOC_TYPE, limit=10, skip=20)
        req = transport.last_request
        assert req is not None
        assert req.params.get("limit") == "10"
        assert req.params.get("skip") == "20"

    def test_omits_limit_and_skip_when_none(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_api(transport)
        api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert "limit" not in req.params
        assert "skip" not in req.params

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_api(transport, token=_TOKEN)
        api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_empty_results(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_api(transport)
        result = api.search_documents(_DOC_TYPE)
        assert result.total_count == 0
        assert result.results == []

    def test_results_missing_defaults_to_empty_list(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0}))
        api = _make_api(transport)
        result = api.search_documents(_DOC_TYPE)
        assert result.results == []


# ---------------------------------------------------------------------------
# get_document_content — sync
# ---------------------------------------------------------------------------


class TestGetDocumentContent:
    def test_returns_dict(self) -> None:
        payload = {"docId": _DOC_ID, "content": "some content"}
        transport = StubTransport(response=_ok(payload))
        api = _make_api(transport)
        result = api.get_document_content(_DOC_ID)
        assert isinstance(result, dict)
        assert result["docId"] == _DOC_ID

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        api.get_document_content(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/documents/content"

    def test_sends_oms_id_and_doc_id(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        api.get_document_content(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("docId") == _DOC_ID

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport, token=_TOKEN)
        api.get_document_content(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_sends_accept_json_header(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        api.get_document_content(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# delete_document — sync
# ---------------------------------------------------------------------------


class TestDeleteDocument:
    def test_returns_delete_document_response(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        result = api.delete_document(_DOC_ID)
        assert isinstance(result, DeleteDocumentResponse)
        assert result.success is True

    def test_success_false_when_missing(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        result = api.delete_document(_DOC_ID)
        assert result.success is False

    def test_sends_delete_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.delete_document(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "DELETE"
        assert req.path == "/api/v3/documents/delete"

    def test_sends_oms_id_and_doc_id(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.delete_document(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("docId") == _DOC_ID

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport, token=_TOKEN)
        api.delete_document(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_sends_accept_json_header(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.delete_document(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# sign_document — sync
# ---------------------------------------------------------------------------


class TestSignDocument:
    def test_returns_sign_document_response(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        result = api.sign_document(_DOC_ID, _SIGNATURE)
        assert isinstance(result, SignDocumentResponse)
        assert result.success is True

    def test_success_false_when_missing(self) -> None:
        transport = StubTransport(response=_ok({}))
        api = _make_api(transport)
        result = api.sign_document(_DOC_ID, _SIGNATURE)
        assert result.success is False

    def test_sends_post_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.method == "POST"
        assert req.path == "/api/v3/documents/sign"

    def test_sends_oms_id_query_param(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    def test_sends_json_body_with_doc_id_and_signature(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.json_body is not None
        assert req.json_body.get("docId") == _DOC_ID
        assert req.json_body.get("signature") == _SIGNATURE

    def test_does_not_send_x_signature_header(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert "X-Signature" not in req.headers

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport, token=_TOKEN)
        api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_sends_content_type_json_header(self) -> None:
        transport = StubTransport(response=_ok({"success": True}))
        api = _make_api(transport)
        api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Content-Type") == "application/json"


# ---------------------------------------------------------------------------
# SuzClient wiring — sync
# ---------------------------------------------------------------------------


class TestSuzClientWiring:
    def test_client_has_documents_attribute(self) -> None:
        from suz_sdk.client import SuzClient

        transport = StubTransport(response=_ok({}))
        client = SuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        assert isinstance(client.documents, DocumentsApi)

    def test_client_documents_delete_document(self) -> None:
        from suz_sdk.client import SuzClient

        transport = StubTransport(response=_ok({"success": True}))
        client = SuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        result = client.documents.delete_document(_DOC_ID)
        assert result.success is True
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# Async get_receipt_document
# ---------------------------------------------------------------------------


class TestAsyncGetReceiptDocument:
    @pytest.mark.anyio
    async def test_returns_dict(self) -> None:
        payload = {"docId": _RESULT_DOC_ID, "status": "PROCESSED"}
        transport = AsyncStubTransport(response=_ok(payload))
        api = _make_async_api(transport)
        result = await api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        assert isinstance(result, dict)
        assert result["docId"] == _RESULT_DOC_ID

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport)
        await api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/receipts/document"

    @pytest.mark.anyio
    async def test_sends_oms_id_and_result_doc_id(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport)
        await api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("resultDocId") == _RESULT_DOC_ID

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.get_receipt_document(_RESULT_DOC_ID, _DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# Async search_documents
# ---------------------------------------------------------------------------


class TestAsyncSearchDocuments:
    @pytest.mark.anyio
    async def test_returns_search_documents_response(self) -> None:
        docs = [{"docId": "d1"}]
        transport = AsyncStubTransport(response=_ok({"totalCount": 1, "result": docs}))
        api = _make_async_api(transport)
        result = await api.search_documents(_DOC_TYPE)
        assert isinstance(result, SearchDocumentsResponse)
        assert result.total_count == 1
        assert result.results == docs

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_async_api(transport)
        await api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/documents/search"

    @pytest.mark.anyio
    async def test_sends_required_params(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_async_api(transport)
        await api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("documentType") == _DOC_TYPE

    @pytest.mark.anyio
    async def test_sends_optional_limit_and_skip(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_async_api(transport)
        await api.search_documents(_DOC_TYPE, limit=5, skip=10)
        req = transport.last_request
        assert req is not None
        assert req.params.get("limit") == "5"
        assert req.params.get("skip") == "10"

    @pytest.mark.anyio
    async def test_omits_limit_and_skip_when_none(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_async_api(transport)
        await api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert "limit" not in req.params
        assert "skip" not in req.params

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "result": []}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.search_documents(_DOC_TYPE)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# Async get_document_content
# ---------------------------------------------------------------------------


class TestAsyncGetDocumentContent:
    @pytest.mark.anyio
    async def test_returns_dict(self) -> None:
        payload = {"docId": _DOC_ID, "content": "data"}
        transport = AsyncStubTransport(response=_ok(payload))
        api = _make_async_api(transport)
        result = await api.get_document_content(_DOC_ID)
        assert isinstance(result, dict)
        assert result["docId"] == _DOC_ID

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport)
        await api.get_document_content(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/documents/content"

    @pytest.mark.anyio
    async def test_sends_oms_id_and_doc_id(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport)
        await api.get_document_content(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("docId") == _DOC_ID

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.get_document_content(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# Async delete_document
# ---------------------------------------------------------------------------


class TestAsyncDeleteDocument:
    @pytest.mark.anyio
    async def test_returns_delete_document_response(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        result = await api.delete_document(_DOC_ID)
        assert isinstance(result, DeleteDocumentResponse)
        assert result.success is True

    @pytest.mark.anyio
    async def test_success_false_when_missing(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport)
        result = await api.delete_document(_DOC_ID)
        assert result.success is False

    @pytest.mark.anyio
    async def test_sends_delete_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        await api.delete_document(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "DELETE"
        assert req.path == "/api/v3/documents/delete"

    @pytest.mark.anyio
    async def test_sends_oms_id_and_doc_id(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        await api.delete_document(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("docId") == _DOC_ID

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.delete_document(_DOC_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# Async sign_document
# ---------------------------------------------------------------------------


class TestAsyncSignDocument:
    @pytest.mark.anyio
    async def test_returns_sign_document_response(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        result = await api.sign_document(_DOC_ID, _SIGNATURE)
        assert isinstance(result, SignDocumentResponse)
        assert result.success is True

    @pytest.mark.anyio
    async def test_success_false_when_missing(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        api = _make_async_api(transport)
        result = await api.sign_document(_DOC_ID, _SIGNATURE)
        assert result.success is False

    @pytest.mark.anyio
    async def test_sends_post_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        await api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.method == "POST"
        assert req.path == "/api/v3/documents/sign"

    @pytest.mark.anyio
    async def test_sends_oms_id_query_param(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        await api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    @pytest.mark.anyio
    async def test_sends_json_body_with_doc_id_and_signature(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        await api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.json_body is not None
        assert req.json_body.get("docId") == _DOC_ID
        assert req.json_body.get("signature") == _SIGNATURE

    @pytest.mark.anyio
    async def test_does_not_send_x_signature_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport)
        await api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert "X-Signature" not in req.headers

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({"success": True}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.sign_document(_DOC_ID, _SIGNATURE)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# AsyncSuzClient wiring
# ---------------------------------------------------------------------------


class TestAsyncSuzClientWiring:
    def test_client_has_documents_attribute(self) -> None:
        from suz_sdk.async_client import AsyncSuzClient

        transport = AsyncStubTransport(response=_ok({}))
        client = AsyncSuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        assert isinstance(client.documents, AsyncDocumentsApi)

    @pytest.mark.anyio
    async def test_client_documents_sign_document(self) -> None:
        from suz_sdk.async_client import AsyncSuzClient

        transport = AsyncStubTransport(response=_ok({"success": True}))
        client = AsyncSuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        result = await client.documents.sign_document(_DOC_ID, _SIGNATURE)
        assert result.success is True
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

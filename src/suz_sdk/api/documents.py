"""DocumentsApi — document management endpoints.

Endpoints implemented:
    get_receipt_document()  GET    /api/v3/receipts/document
    search_documents()      GET    /api/v3/documents/search
    get_document_content()  GET    /api/v3/documents/content
    delete_document()       DELETE /api/v3/documents/delete
    sign_document()         POST   /api/v3/documents/sign
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from suz_sdk.transport.base import BaseTransport, Request

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


@dataclass
class SearchDocumentsResponse:
    """Response from GET /api/v3/documents/search.

    Attributes:
        total_count: Total number of matching documents.
        results:     Page of document dicts (schema varies by documentType).
    """

    total_count: int
    results: list[dict[str, Any]]


@dataclass
class DeleteDocumentResponse:
    """Response from DELETE /api/v3/documents/delete.

    Attributes:
        success: True when the document was successfully deleted.
    """

    success: bool = False


@dataclass
class SignDocumentResponse:
    """Response from POST /api/v3/documents/sign.

    Attributes:
        success: True when the document was successfully signed.
    """

    success: bool = False


# ---------------------------------------------------------------------------
# Sync API class
# ---------------------------------------------------------------------------


class DocumentsApi:
    """Client for document management endpoints.

    Instantiated and owned by SuzClient — access via ``client.documents``.

    Args:
        transport:        HTTP transport to use for requests.
        oms_id:           СУЗ instance UUID, sent as the ``omsId`` query param.
        get_auth_headers: Callable returning current authorization headers.
    """

    def __init__(
        self,
        transport: BaseTransport,
        oms_id: str,
        get_auth_headers: Callable[[], dict[str, str]],
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_receipt_document(self, result_doc_id: str) -> dict[str, Any]:
        """Retrieve a receipt document by its result doc ID.

        GET /api/v3/receipts/document?omsId={omsId}&resultDocId={resultDocId}

        Args:
            result_doc_id: The resultDocId of the receipt document to retrieve.

        Returns:
            Raw response dict (schema is complex and product-group-specific).

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="GET",
            path="/api/v3/receipts/document",
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
        return dict(resp.body)

    def search_documents(
        self,
        document_type: str,
        limit: int | None = None,
        skip: int | None = None,
    ) -> SearchDocumentsResponse:
        """Search documents by type with optional pagination.

        GET /api/v3/documents/search?omsId={omsId}&documentType={documentType}
                                     [&limit={limit}][&skip={skip}]

        Args:
            document_type: Type code of the documents to search for.
            limit:         Optional maximum number of records to return.
            skip:          Optional number of records to skip (offset).

        Returns:
            SearchDocumentsResponse with total_count and results list.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        params: dict[str, str] = {
            "omsId": self._oms_id,
            "documentType": document_type,
        }
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/documents/search",
            params=params,
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return SearchDocumentsResponse(
            total_count=body["totalCount"],
            results=body.get("results", []),
        )

    def get_document_content(self, doc_id: str) -> dict[str, Any]:
        """Retrieve the content of a document by its doc ID.

        GET /api/v3/documents/content?omsId={omsId}&docId={docId}

        Args:
            doc_id: The docId of the document to retrieve.

        Returns:
            Raw response dict (schema varies by document type).

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="GET",
            path="/api/v3/documents/content",
            params={
                "omsId": self._oms_id,
                "docId": doc_id,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        return dict(resp.body)

    def delete_document(self, doc_id: str) -> DeleteDocumentResponse:
        """Delete a document by its doc ID.

        DELETE /api/v3/documents/delete?omsId={omsId}&docId={docId}

        Args:
            doc_id: The docId of the document to delete.

        Returns:
            DeleteDocumentResponse with success flag.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="DELETE",
            path="/api/v3/documents/delete",
            params={
                "omsId": self._oms_id,
                "docId": doc_id,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return DeleteDocumentResponse(success=body.get("success", False))

    def sign_document(self, doc_id: str, signature: str) -> SignDocumentResponse:
        """Sign a document by submitting its docId and detached signature.

        POST /api/v3/documents/sign?omsId={omsId}

        The signature is passed in the request body — no X-Signature header
        is required for this endpoint.

        Args:
            doc_id:    The docId of the document to sign.
            signature: Base64-encoded detached CMS signature of the document.

        Returns:
            SignDocumentResponse with success flag.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="POST",
            path="/api/v3/documents/sign",
            params={"omsId": self._oms_id},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
            json_body={"docId": doc_id, "signature": signature},
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return SignDocumentResponse(success=body.get("success", False))


# ---------------------------------------------------------------------------
# Async API class
# ---------------------------------------------------------------------------


class AsyncDocumentsApi:
    """Async client for document management endpoints.

    Instantiated and owned by AsyncSuzClient — access via ``client.documents``.

    Args:
        transport:        Async HTTP transport to use for requests.
        oms_id:           СУЗ instance UUID, sent as the ``omsId`` query param.
        get_auth_headers: Async callable returning current authorization headers.
    """

    def __init__(
        self,
        transport: object,
        oms_id: str,
        get_auth_headers: Callable[[], Awaitable[dict[str, str]]],
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_receipt_document(self, result_doc_id: str) -> dict[str, Any]:
        """Retrieve a receipt document by its result doc ID.

        GET /api/v3/receipts/document?omsId={omsId}&resultDocId={resultDocId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="GET",
            path="/api/v3/receipts/document",
            params={
                "omsId": self._oms_id,
                "resultDocId": result_doc_id,
            },
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        return dict(resp.body)

    async def search_documents(
        self,
        document_type: str,
        limit: int | None = None,
        skip: int | None = None,
    ) -> SearchDocumentsResponse:
        """Search documents by type with optional pagination.

        GET /api/v3/documents/search?omsId={omsId}&documentType={documentType}
                                     [&limit={limit}][&skip={skip}]
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        params: dict[str, str] = {
            "omsId": self._oms_id,
            "documentType": document_type,
        }
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/documents/search",
            params=params,
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return SearchDocumentsResponse(
            total_count=body["totalCount"],
            results=body.get("results", []),
        )

    async def get_document_content(self, doc_id: str) -> dict[str, Any]:
        """Retrieve the content of a document by its doc ID.

        GET /api/v3/documents/content?omsId={omsId}&docId={docId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="GET",
            path="/api/v3/documents/content",
            params={
                "omsId": self._oms_id,
                "docId": doc_id,
            },
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        return dict(resp.body)

    async def delete_document(self, doc_id: str) -> DeleteDocumentResponse:
        """Delete a document by its doc ID.

        DELETE /api/v3/documents/delete?omsId={omsId}&docId={docId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="DELETE",
            path="/api/v3/documents/delete",
            params={
                "omsId": self._oms_id,
                "docId": doc_id,
            },
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return DeleteDocumentResponse(success=body.get("success", False))

    async def sign_document(self, doc_id: str, signature: str) -> SignDocumentResponse:
        """Sign a document by submitting its docId and detached signature.

        POST /api/v3/documents/sign?omsId={omsId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="POST",
            path="/api/v3/documents/sign",
            params={"omsId": self._oms_id},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
            json_body={"docId": doc_id, "signature": signature},
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return SignDocumentResponse(success=body.get("success", False))

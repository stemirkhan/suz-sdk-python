"""True API (GIS MT) authentication flow for the SUZ SDK (§9.3.2).

Implements the two-step challenge-sign flow used to obtain a clientToken
for accessing СУЗ API methods.

Flow (§9.3.2.1 + §9.3.2.2):
    Step 1 — GET /auth/key
        Returns a random challenge: {"uuid": "...", "data": "..."}

    Step 2 — POST /auth/simpleSignIn/{omsConnection}
        Body: {"uuid": "<from step 1>", "data": "<signed challenge, base64>"}
        Returns: {"token": "<clientToken>"}  — valid for 10 hours.

True API base URLs (§9.3.2):
    Sandbox:    https://markirovka.sandbox.crptech.ru/api/v3/true-api
    Production: https://markirovka.crpt.ru/api/v3/true-api

Notes:
    - The ``data`` field in the step-2 body is the raw challenge bytes signed
      with the UOT certificate using an attached CMS signature, Base64-encoded.
    - The returned token is passed as the ``clientToken`` header in all
      subsequent SUZ API calls.
    - Token TTL is 10 hours (Table 380).  Re-issuing a token immediately
      invalidates the previous one (§9.2 footnote).
"""

from suz_sdk.exceptions import SuzAuthError
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import BaseTransport, Request


class TrueApiAuth:
    """Implements the True API two-step authentication flow (§9.3.2).

    Args:
        oms_connection: UUID of the registered integration installation.
                        Sent as the path parameter in step 2.
        signer:         Signer that produces a Base64 signature of the
                        challenge data bytes.  The underlying implementation
                        must use an attached CMS signature with the UOT
                        certificate (§9.3.2.2, Table 379).
        transport:      HTTP transport configured with the True API base URL
                        (e.g. https://markirovka.sandbox.crptech.ru/api/v3/true-api).
    """

    def __init__(
        self,
        oms_connection: str,
        signer: BaseSigner,
        transport: BaseTransport,
    ) -> None:
        self._oms_connection = oms_connection
        self._signer = signer
        self._transport = transport

    def fetch_token(self) -> str:
        """Execute the two-step True API auth flow and return a clientToken.

        Returns:
            clientToken string, valid for 10 hours.

        Raises:
            SuzAuthError:       Auth challenge failed or server returned no token.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request exceeded timeout.
            SuzApiError:        Unexpected server error.
        """
        # Step 1: obtain the challenge UUID and random data string.
        auth_key_resp = self._transport.request(
            Request(
                method="GET",
                path="/auth/key",
                headers={"Accept": "application/json"},
            )
        )
        challenge: dict[str, str] = auth_key_resp.body  # type: ignore[assignment]
        uuid = challenge.get("uuid")
        data = challenge.get("data")
        if not uuid or not data:
            raise SuzAuthError(
                "True API /auth/key returned unexpected payload: "
                f"uuid={uuid!r}, data={data!r}"
            )

        # Step 2: sign the challenge and exchange for a token.
        signed_data = self._signer.sign_bytes(data.encode())
        token_resp = self._transport.request(
            Request(
                method="POST",
                path=f"/auth/simpleSignIn/{self._oms_connection}",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json_body={"uuid": uuid, "data": signed_data},
            )
        )
        payload: dict[str, str] = token_resp.body  # type: ignore[assignment]
        token = payload.get("token") or payload.get("uuidToken")
        if not token:
            raise SuzAuthError(
                f"True API returned no token. Response: {payload!r}"
            )
        return token

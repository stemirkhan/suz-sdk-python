"""Async True API authentication flow (§9.3.2)."""

from suz_sdk.exceptions import SuzAuthError
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport
from suz_sdk.transport.base import Request


class AsyncTrueApiAuth:
    """Async implementation of the True API two-step auth flow (§9.3.2).

    Args:
        oms_connection: UUID of the registered integration installation.
        signer:         Signer for the challenge bytes (attached CMS, Base64).
        transport:      Async transport configured with the True API base URL.
    """

    def __init__(
        self,
        oms_connection: str,
        signer: BaseSigner,
        transport: AsyncHttpxTransport,
    ) -> None:
        self._oms_connection = oms_connection
        self._signer = signer
        self._transport = transport

    async def fetch_token(self) -> str:
        """Execute the two-step True API auth flow and return a clientToken.

        Returns:
            clientToken string, valid for 10 hours.

        Raises:
            SuzAuthError:       Auth challenge failed or server returned no token.
            SuzTransportError:  Network-level failure.
        """
        auth_key_resp = await self._transport.request(
            Request(
                method="GET",
                path="/auth/key",
                headers={"Accept": "application/json"},
            )
        )
        challenge: dict[str, str] = auth_key_resp.body
        uuid = challenge.get("uuid")
        data = challenge.get("data")
        if not uuid or not data:
            raise SuzAuthError(
                "True API /auth/key returned unexpected payload: "
                f"uuid={uuid!r}, data={data!r}"
            )

        signed_data = self._signer.sign_bytes(data.encode())
        token_resp = await self._transport.request(
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
        payload: dict[str, str] = token_resp.body
        token = payload.get("token") or payload.get("uuidToken")
        if not token:
            raise SuzAuthError(
                f"True API returned no token. Response: {payload!r}"
            )
        return token

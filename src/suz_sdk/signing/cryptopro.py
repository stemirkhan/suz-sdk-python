"""CryptoProSigner — GOST signing via the CryptoPro CSP cryptcp CLI tool.

CryptoPro CSP is the Russian cryptographic provider used by CRPT/ЧЗ systems.
It implements GOST R 34.10-2012 signing and GOST R 34.11-2012 hashing, which
are required by the СУЗ API for the X-Signature header (§2.3.1).

This signer delegates to the ``cryptcp`` command-line utility bundled with
CryptoPro CSP, producing a detached DER-encoded CMS (PKCS#7) signature and
returning it Base64-encoded — the exact format expected by the API.

Typical Linux installation path:
    /opt/cprocsp/bin/amd64/cryptcp

Usage:
    signer = CryptoProSigner(thumbprint="A1B2C3...", cryptcp_path="/opt/cprocsp/bin/amd64/cryptcp")
    client = SuzClient(oms_id="...", signer=signer, ...)
"""

import base64
import subprocess
import tempfile
from pathlib import Path

from suz_sdk.exceptions import SuzSigningError


class CryptoProSigner:
    """Signs data with CryptoPro CSP via the cryptcp command-line utility.

    Produces a detached DER-encoded CMS signature using GOST R 34.10-2012,
    Base64-encoded — suitable for the X-Signature HTTP header (§2.3.1).

    CryptoPro CSP must be installed on the system.  The certificate
    identified by ``thumbprint`` must be present in the ``My`` (personal)
    certificate store for the current user or for the SYSTEM account (when
    running as a service).

    Args:
        thumbprint:    SHA-1 thumbprint of the signing certificate,
                       hex string, case-insensitive (40 characters).
                       Example: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        cryptcp_path:  Path to the cryptcp binary.
                       Default: "cryptcp" (requires it to be on PATH).
                       Linux typical path:
                       "/opt/cprocsp/bin/amd64/cryptcp"
        nochain:       Pass ``-nochain`` to cryptcp — omit the certificate
                       chain from the signature.  Useful when the full chain
                       is not installed in the store.  Default: False.
        nopolicy:      Pass ``-nopolicy`` to cryptcp — skip certificate
                       policy validation.  Default: False.
        extra_args:    Additional arguments inserted before the input file
                       path.  Use to pass any non-standard cryptcp flags.
        timeout:       Subprocess timeout in seconds.  Default: 30.
    """

    def __init__(
        self,
        thumbprint: str,
        cryptcp_path: str = "cryptcp",
        nochain: bool = False,
        nopolicy: bool = False,
        extra_args: list[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._thumbprint = thumbprint
        self._cryptcp_path = cryptcp_path
        self._nochain = nochain
        self._nopolicy = nopolicy
        self._extra_args = extra_args or []
        self._timeout = timeout

    def sign_bytes(self, payload: bytes) -> str:
        """Sign *payload* and return a Base64-encoded detached CMS signature.

        Writes the payload to a temporary file, invokes ``cryptcp -sign``
        with the configured options, reads the output ``.sig`` file and
        returns its content Base64-encoded.

        Args:
            payload: Raw bytes to sign (POST body or GET path+query).

        Returns:
            Base64-encoded detached DER CMS signature string.

        Raises:
            SuzSigningError: If cryptcp is not found, exits non-zero, or
                             the output signature file is not produced.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            infile = tmp / "data.bin"
            outfile = tmp / "data.sig"
            infile.write_bytes(payload)

            cmd = self._build_command(str(infile), str(outfile))

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                )
            except FileNotFoundError:
                raise SuzSigningError(
                    f"cryptcp not found at {self._cryptcp_path!r}. "
                    "Install CryptoPro CSP and set cryptcp_path to the correct path, "
                    "e.g. '/opt/cprocsp/bin/amd64/cryptcp'."
                ) from None
            except subprocess.TimeoutExpired:
                raise SuzSigningError(
                    f"cryptcp timed out after {self._timeout}s."
                ) from None

            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise SuzSigningError(
                    f"cryptcp exited with code {result.returncode}: {detail}"
                )

            if not outfile.exists():
                raise SuzSigningError(
                    "cryptcp succeeded but the output signature file was not created. "
                    f"Command: {' '.join(cmd)}"
                )

            return base64.b64encode(outfile.read_bytes()).decode("ascii")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_command(self, infile: str, outfile: str) -> list[str]:
        cmd = [
            self._cryptcp_path,
            "-sign",
            "-thumbprint", self._thumbprint,
            "-der",
            "-detached",
        ]
        if self._nochain:
            cmd.append("-nochain")
        if self._nopolicy:
            cmd.append("-nopolicy")
        cmd.extend(self._extra_args)
        cmd.extend([infile, outfile])
        return cmd

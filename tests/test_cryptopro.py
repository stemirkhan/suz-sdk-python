"""Unit tests for CryptoProSigner."""

import base64
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from suz_sdk.exceptions import SuzSigningError
from suz_sdk.signing.cryptopro import CryptoProSigner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

THUMBPRINT = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
FAKE_SIG = b"\xde\xad\xbe\xef\xca\xfe\xba\xbe"


def _make_signer(**kwargs) -> CryptoProSigner:
    defaults = {"thumbprint": THUMBPRINT}
    defaults.update(kwargs)
    return CryptoProSigner(**defaults)


def _make_run_mock(sig_bytes: bytes = FAKE_SIG, returncode: int = 0):
    """Return a mock for subprocess.run that writes sig_bytes to the output file."""

    def side_effect(cmd, **kwargs):
        outfile = Path(cmd[-1])
        if returncode == 0:
            outfile.write_bytes(sig_bytes)
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="")

    mock = MagicMock(side_effect=side_effect)
    return mock


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_returns_base64_encoded_signature(self):
        with patch("subprocess.run", _make_run_mock(FAKE_SIG)):
            result = _make_signer().sign_bytes(b"hello")
        assert result == base64.b64encode(FAKE_SIG).decode("ascii")

    def test_returns_string(self):
        with patch("subprocess.run", _make_run_mock()):
            result = _make_signer().sign_bytes(b"data")
        assert isinstance(result, str)

    def test_different_payloads_produce_same_sig_bytes_from_mock(self):
        # The mock always returns the same FAKE_SIG regardless of payload;
        # this just confirms we pass through whatever cryptcp produces.
        with patch("subprocess.run", _make_run_mock(b"sig-a")):
            r1 = _make_signer().sign_bytes(b"payload-1")
        with patch("subprocess.run", _make_run_mock(b"sig-b")):
            r2 = _make_signer().sign_bytes(b"payload-2")
        assert r1 != r2


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


class TestCommandConstruction:
    def _capture_cmd(self, signer: CryptoProSigner, payload: bytes = b"x") -> list[str]:
        captured = {}

        def side_effect(cmd, **kwargs):
            captured["cmd"] = cmd
            Path(cmd[-1]).write_bytes(FAKE_SIG)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=side_effect):
            signer.sign_bytes(payload)
        return captured["cmd"]

    def test_cryptcp_binary_first(self):
        cmd = self._capture_cmd(_make_signer(cryptcp_path="cryptcp"))
        assert cmd[0] == "cryptcp"

    def test_custom_cryptcp_path(self):
        cmd = self._capture_cmd(_make_signer(cryptcp_path="/opt/cprocsp/bin/amd64/cryptcp"))
        assert cmd[0] == "/opt/cprocsp/bin/amd64/cryptcp"

    def test_sign_flag(self):
        cmd = self._capture_cmd(_make_signer())
        assert "-sign" in cmd

    def test_thumbprint_in_command(self):
        cmd = self._capture_cmd(_make_signer())
        idx = cmd.index("-thumbprint")
        assert cmd[idx + 1] == THUMBPRINT

    def test_der_flag(self):
        cmd = self._capture_cmd(_make_signer())
        assert "-der" in cmd

    def test_detached_flag(self):
        cmd = self._capture_cmd(_make_signer())
        assert "-detached" in cmd

    def test_nochain_not_included_by_default(self):
        cmd = self._capture_cmd(_make_signer())
        assert "-nochain" not in cmd

    def test_nochain_included_when_true(self):
        cmd = self._capture_cmd(_make_signer(nochain=True))
        assert "-nochain" in cmd

    def test_nopolicy_not_included_by_default(self):
        cmd = self._capture_cmd(_make_signer())
        assert "-nopolicy" not in cmd

    def test_nopolicy_included_when_true(self):
        cmd = self._capture_cmd(_make_signer(nopolicy=True))
        assert "-nopolicy" in cmd

    def test_extra_args_included(self):
        cmd = self._capture_cmd(_make_signer(extra_args=["-silent", "-my"]))
        assert "-silent" in cmd
        assert "-my" in cmd

    def test_infile_and_outfile_are_last_two_args(self):
        cmd = self._capture_cmd(_make_signer())
        # Both should be absolute paths to temp files
        assert Path(cmd[-2]).is_absolute()
        assert Path(cmd[-1]).is_absolute()

    def test_infile_different_from_outfile(self):
        cmd = self._capture_cmd(_make_signer())
        assert cmd[-2] != cmd[-1]

    def test_payload_written_to_infile(self):
        payload = b"payload-bytes"
        written = {}

        def side_effect(cmd, **kwargs):
            written["data"] = Path(cmd[-2]).read_bytes()
            Path(cmd[-1]).write_bytes(FAKE_SIG)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=side_effect):
            _make_signer().sign_bytes(payload)

        assert written["data"] == payload


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_raises_on_nonzero_exit(self):
        with patch("subprocess.run", _make_run_mock(returncode=1)):
            with pytest.raises(SuzSigningError, match="exited with code 1"):
                _make_signer().sign_bytes(b"data")

    def test_error_message_includes_stderr(self):
        def side_effect(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="Certificate not found")

        with patch("subprocess.run", side_effect=side_effect):
            with pytest.raises(SuzSigningError, match="Certificate not found"):
                _make_signer().sign_bytes(b"data")

    def test_raises_on_file_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("No such file")):
            with pytest.raises(SuzSigningError, match="cryptcp not found"):
                _make_signer(cryptcp_path="/bad/path/cryptcp").sign_bytes(b"data")

    def test_error_mentions_cryptcp_path(self):
        path = "/my/custom/cryptcp"
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(SuzSigningError, match=path):
                _make_signer(cryptcp_path=path).sign_bytes(b"data")

    def test_raises_on_timeout(self):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="cryptcp", timeout=30),
        ):
            with pytest.raises(SuzSigningError, match="timed out"):
                _make_signer().sign_bytes(b"data")

    def test_raises_when_outfile_not_created(self):
        """Cryptcp exits 0 but produces no output file (should not happen but guard it)."""

        def side_effect(cmd, **kwargs):
            # do NOT write the output file
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=side_effect):
            with pytest.raises(SuzSigningError, match="output signature file was not created"):
                _make_signer().sign_bytes(b"data")

    def test_suz_signing_error_is_suz_error(self):
        from suz_sdk.exceptions import SuzError

        with patch("subprocess.run", _make_run_mock(returncode=1)):
            with pytest.raises(SuzError):
                _make_signer().sign_bytes(b"data")


# ---------------------------------------------------------------------------
# build_command unit tests (private method, tested directly for clarity)
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_basic_command_structure(self):
        signer = CryptoProSigner(thumbprint="ABCD", cryptcp_path="cryptcp")
        cmd = signer._build_command("/in/data.bin", "/out/data.sig")
        assert cmd[0] == "cryptcp"
        assert "-sign" in cmd
        assert "-thumbprint" in cmd
        assert "ABCD" in cmd
        assert "-der" in cmd
        assert "-detached" in cmd
        assert cmd[-2] == "/in/data.bin"
        assert cmd[-1] == "/out/data.sig"

    def test_nochain_in_command(self):
        signer = CryptoProSigner(thumbprint="X", nochain=True)
        cmd = signer._build_command("in", "out")
        assert "-nochain" in cmd

    def test_nopolicy_in_command(self):
        signer = CryptoProSigner(thumbprint="X", nopolicy=True)
        cmd = signer._build_command("in", "out")
        assert "-nopolicy" in cmd

    def test_extra_args_before_files(self):
        signer = CryptoProSigner(thumbprint="X", extra_args=["-foo", "-bar"])
        cmd = signer._build_command("in", "out")
        foo_idx = cmd.index("-foo")
        in_idx = cmd.index("in")
        assert foo_idx < in_idx


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_implements_base_signer_protocol(self):
        from suz_sdk.signing.base import BaseSigner

        signer = CryptoProSigner(thumbprint=THUMBPRINT)
        assert isinstance(signer, BaseSigner)

    def test_exported_from_suz_sdk(self):
        from suz_sdk import CryptoProSigner as Imported

        assert Imported is CryptoProSigner

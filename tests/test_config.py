"""Tests for SuzConfig and Environment."""

import pytest
from pydantic import ValidationError

from suz_sdk.config import Environment, SuzConfig


class TestEnvironment:
    def test_sandbox_value(self) -> None:
        assert Environment.SANDBOX == "sandbox"

    def test_production_value(self) -> None:
        assert Environment.PRODUCTION == "production"


class TestSuzConfig:
    def test_minimal_config(self) -> None:
        cfg = SuzConfig(oms_id="cdf12109-10d3-11e6-8b6f-0050569977a1")
        assert cfg.oms_id == "cdf12109-10d3-11e6-8b6f-0050569977a1"
        assert cfg.environment == Environment.SANDBOX
        assert cfg.base_url is None
        assert cfg.client_token is None
        assert cfg.signer is None
        assert cfg.timeout == 30.0
        assert cfg.verify_ssl is True

    def test_resolved_base_url_sandbox_default(self) -> None:
        cfg = SuzConfig(oms_id="abc", environment=Environment.SANDBOX)
        assert cfg.resolved_base_url() == "https://suz-integrator.sandbox.crptech.ru"

    def test_resolved_base_url_production_default(self) -> None:
        cfg = SuzConfig(oms_id="abc", environment=Environment.PRODUCTION)
        assert cfg.resolved_base_url() == "https://suzgrid.crpt.ru:16443"

    def test_resolved_base_url_explicit_override(self) -> None:
        cfg = SuzConfig(
            oms_id="abc",
            environment=Environment.SANDBOX,
            base_url="https://my-custom-oms.example.com",
        )
        assert cfg.resolved_base_url() == "https://my-custom-oms.example.com"

    def test_trailing_slash_stripped_from_base_url(self) -> None:
        cfg = SuzConfig(oms_id="abc", base_url="https://example.com/")
        assert cfg.resolved_base_url() == "https://example.com"

    def test_timeout_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            SuzConfig(oms_id="abc", timeout=0)

    def test_timeout_must_be_positive_negative(self) -> None:
        with pytest.raises(ValidationError):
            SuzConfig(oms_id="abc", timeout=-5)

    def test_custom_timeout(self) -> None:
        cfg = SuzConfig(oms_id="abc", timeout=60.0)
        assert cfg.timeout == 60.0

    def test_optional_fields_none_by_default(self) -> None:
        cfg = SuzConfig(oms_id="abc")
        assert cfg.oms_connection is None
        assert cfg.registration_key is None

    def test_all_fields(self) -> None:
        cfg = SuzConfig(
            oms_id="abc",
            environment=Environment.PRODUCTION,
            base_url="https://example.com",
            client_token="tok-123",
            oms_connection="conn-456",
            registration_key="reg-789",
            timeout=10.0,
            verify_ssl=False,
            user_agent="my-app/1.0",
        )
        assert cfg.client_token == "tok-123"
        assert cfg.oms_connection == "conn-456"
        assert cfg.registration_key == "reg-789"
        assert cfg.verify_ssl is False
        assert cfg.user_agent == "my-app/1.0"

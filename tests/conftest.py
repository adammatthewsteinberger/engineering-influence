"""Shared fixtures."""

import os
import shutil
from pathlib import Path

# pypdf 7 compares the jbig2dec path its filters module found on import with the default configuration. filters is
# otherwise imported lazily by the first reader, which can be inside a test that narrows PATH; import it here, before any
# test runs, so the two always agree.
import pypdf.filters  # noqa: F401
import pytest
from paid_gate import PaidGate

from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interactions.api.api_guard import ApiGuard

TEST_API_KEY = "test-api-key-0123456789abcdef"  # gitleaks:allow


def pytest_configure(config: pytest.Config) -> None:
    """Lock every test marked ``paid`` behind EI_ALLOW_PAID=1 (see tests/paid_gate.py)."""
    config.pluginmanager.register(PaidGate(os.environ), "paid-gate")


@pytest.fixture
def api_key() -> str:
    """A key the shared guard accepts."""
    return TEST_API_KEY


@pytest.fixture
def api_guard() -> ApiGuard:
    """A guard with generous limits and one valid key."""
    return ApiGuard(
        ConstantTimeApiKeyVerifier([TEST_API_KEY]),
        TokenBucketRateLimiter(burst=100, per_second=100),
    )


@pytest.fixture(scope="session")
def migrated_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One SQLite database brought to the latest revision, copied for each test that needs one."""
    template = tmp_path_factory.mktemp("schema") / "template.db"
    SchemaMigrator().upgrade(f"sqlite:///{template}")
    return template


@pytest.fixture
def database_url(tmp_path: Path, migrated_template: Path) -> str:
    """A fresh, migrated SQLite database owned by this test."""
    database = tmp_path / "ei.db"
    shutil.copy(migrated_template, database)
    return f"sqlite:///{database}"

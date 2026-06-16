import os
import uuid

import pytest


DEFAULT_E2E_BASE_URL = "http://127.0.0.1:5010"
DEFAULT_E2E_ADMIN_USERNAME = "e2e_admin"
DEFAULT_E2E_ADMIN_PASSWORD = "e2e_password_123"

os.environ.setdefault("E2E_BASE_URL", DEFAULT_E2E_BASE_URL)
os.environ.setdefault("E2E_ADMIN_USERNAME", DEFAULT_E2E_ADMIN_USERNAME)
os.environ.setdefault("E2E_ADMIN_PASSWORD", DEFAULT_E2E_ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def base_url() -> str:
    return DEFAULT_E2E_BASE_URL


@pytest.fixture(scope="session")
def admin_username() -> str:
    return DEFAULT_E2E_ADMIN_USERNAME


@pytest.fixture(scope="session")
def admin_password() -> str:
    return DEFAULT_E2E_ADMIN_PASSWORD


@pytest.fixture()
def unique_post() -> dict[str, str]:
    nonce = uuid.uuid4().hex[:8]
    title = f"E2E Post {nonce}"
    return {
        "title": title,
        "updated_title": f"{title} Updated",
        "content": "# Hello from E2E\n\nThis post was created by Playwright.",
        "updated_content": "# Edited by E2E\n\nThis content was updated by Playwright.",
    }

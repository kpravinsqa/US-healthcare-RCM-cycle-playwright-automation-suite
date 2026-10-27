"""
Root pytest configuration.

* Starts the bundled mock application once per session on a free port
  (set ``BASE_URL`` to point the suite at a real deployed environment).
* Overrides pytest-playwright's ``base_url`` so ``page.goto("/login.html")`` works.
* Resets server state before every test for full isolation.
* Provides an authenticated ``api`` request context and ``logged_in_page``.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.request

import pytest

from config.settings import settings
from mock_app.server import create_server
from utils.logger import get_logger

log = get_logger(__name__)


@pytest.fixture(scope="session")
def app_url():
    external = os.getenv("BASE_URL")
    if external:
        log.info("Running against external environment %s", external)
        yield external.rstrip("/")
        return
    server = create_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    log.info("Mock application started at %s", url)
    yield url
    server.shutdown()


@pytest.fixture(scope="session")
def base_url(app_url):
    return app_url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url):
    return {**browser_context_args, "base_url": base_url, "viewport": {"width": 1366, "height": 768}}


@pytest.fixture(autouse=True)
def reset_application_state(app_url):
    """Each test starts from a known seed data set."""
    if os.getenv("BASE_URL"):
        yield
        return
    req = urllib.request.Request(f"{app_url}/api/test/reset", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()
    yield


@pytest.fixture
def anon_api(playwright, base_url):
    ctx = playwright.request.new_context(base_url=base_url)
    yield ctx
    ctx.dispose()


@pytest.fixture
def api(playwright, base_url):
    """API request context already authenticated as the default test user."""
    bootstrap = playwright.request.new_context(base_url=base_url)
    resp = bootstrap.post("/api/auth/login", data=json.dumps(settings.default_credentials),
                          headers={"Content-Type": "application/json"})
    assert resp.ok, f"Login for API fixture failed: {resp.status} {resp.text()}"
    token = resp.json()["token"]
    bootstrap.dispose()
    ctx = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    yield ctx
    ctx.dispose()


@pytest.fixture
def logged_in_page(page):
    from pages.login_page import LoginPage

    login = LoginPage(page)
    login.open()
    login.login(**settings.default_credentials)
    login.wait_for_post_login()
    return page

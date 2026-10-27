"""Authentication & role-based access — manual suite TS-01."""
import re

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.login_page import LoginPage


@pytest.mark.ui
@pytest.mark.smoke
@pytest.mark.parametrize("creds, landing, badge", [
    (("billing_admin", "Health@123"), "patients.html", "Billing Admin"),
    (("front_desk", "Health@123"), "patients.html", "Front Desk"),
    (("dr_smith", "Health@123"), "dashboard.html", "Dr. John Smith"),
], ids=["admin", "front-desk", "provider"])
def test_each_role_lands_on_its_home_page(page: Page, creds, landing, badge):
    login = LoginPage(page).open()
    login.login(*creds)
    expect(page).to_have_url(re.compile(f".*/{landing}$"))
    expect(login.user_badge).to_have_text(badge)


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize("username, password", [("billing_admin", "wrong"), ("nobody", "Health@123"), ("BILLING_ADMIN", "Health@123")],
                         ids=["wrong-password", "unknown-user", "username-case-sensitive"])
def test_invalid_login(page: Page, username, password):
    login = LoginPage(page).open()
    login.login(username, password)
    login.expect_form_error("Invalid username or password")


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_required_fields(page: Page):
    login = LoginPage(page).open()
    login.submit.click()
    expect(login.field_error("username")).to_have_text("Username is required")
    expect(login.field_error("password")).to_have_text("Password is required")


@pytest.mark.ui
@pytest.mark.regression
def test_front_desk_menu_hides_billing_modules(page: Page):
    login = LoginPage(page).open()
    login.login(*settings.front_desk)
    login.wait_for_post_login()
    expect(page.get_by_test_id("nav-patients")).to_be_visible()
    expect(page.get_by_test_id("nav-claims")).to_have_count(0)
    expect(page.get_by_test_id("nav-providers")).to_have_count(0)


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_front_desk_direct_url_to_claims_is_denied(page: Page):
    login = LoginPage(page).open()
    login.login(*settings.front_desk)
    login.wait_for_post_login()
    page.goto("/claims.html")
    expect(page.get_by_test_id("access-denied")).to_be_visible()


@pytest.mark.ui
@pytest.mark.smoke
def test_logout(logged_in_page: Page):
    LoginPage(logged_in_page).logout()
    logged_in_page.goto("/patients.html")
    expect(logged_in_page).to_have_url(re.compile(r".*/login\.html$"))

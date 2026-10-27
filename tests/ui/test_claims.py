"""Claims lifecycle: create → scrub/submit → payment posting — manual suite TS-06."""
import pytest
from playwright.sync_api import Page, expect

from api.rcm_client import RcmClient
from pages.claims_page import ClaimsPage
from utils.data_factory import days_ago


@pytest.fixture
def rcm(api) -> RcmClient:
    return RcmClient(api)


@pytest.mark.ui
@pytest.mark.smoke
def test_create_and_submit_claim(logged_in_page: Page, rcm: RcmClient):
    enc = rcm.create_encounter(lines=(("99214", 1), ("85025", 1))).json()
    claims = ClaimsPage(logged_in_page).open()
    claims.create_for(enc["id"])
    claims.expect_toast("Claim CLM-")
    number = claims.rows.first.locator("td").first.inner_text()
    expect(claims.cell(number, "billed")).to_have_text("$203.00")
    expect(claims.cell(number, "status")).to_have_text("DRAFT")
    claims.submit(number)
    expect(claims.cell(number, "status")).to_have_text("SUBMITTED")


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_self_pay_claim_is_rejected_by_scrubber(logged_in_page: Page, rcm: RcmClient):
    enc = rcm.create_encounter(patient_id=102).json()   # Sofia Martinez is Self-Pay
    claim = rcm.create_claim(enc["id"]).json()
    claims = ClaimsPage(logged_in_page).open()
    claims.submit(claim["claim_number"])
    claims.expect_toast("Self-pay encounters are billed to the patient")
    expect(claims.cell(claim["claim_number"], "status")).to_have_text("REJECTED")


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize("age_days, status", [(365, "SUBMITTED"), (366, "REJECTED")], ids=["day-365-ok", "day-366-late"])
def test_timely_filing_boundary(logged_in_page: Page, rcm: RcmClient, age_days, status):
    enc = rcm.create_encounter(dos=days_ago(age_days)).json()
    claim = rcm.create_claim(enc["id"]).json()
    claims = ClaimsPage(logged_in_page).open()
    claims.submit(claim["claim_number"])
    expect(claims.cell(claim["claim_number"], "status")).to_have_text(status)


@pytest.mark.ui
@pytest.mark.regression
def test_partial_then_full_payment(logged_in_page: Page, rcm: RcmClient):
    enc = rcm.create_encounter(lines=(("99214", 1),)).json()              # $175
    claim = rcm.create_claim(enc["id"]).json()
    rcm.submit_claim(claim["id"])
    number = claim["claim_number"]
    claims = ClaimsPage(logged_in_page).open()

    claims.post_payment(number, paid=100, adjustment=25)
    expect(claims.cell(number, "status")).to_have_text("PARTIALLY_PAID")
    expect(claims.cell(number, "balance")).to_have_text("$50.00")

    claims.post_payment(number, paid=50)
    expect(claims.cell(number, "status")).to_have_text("PAID")
    expect(claims.cell(number, "balance")).to_have_text("$0.00")


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_overpayment_is_blocked(logged_in_page: Page, rcm: RcmClient):
    claim = rcm.create_claim(rcm.create_encounter().json()["id"]).json()     # $120
    rcm.submit_claim(claim["id"])
    claims = ClaimsPage(logged_in_page).open()
    claims.post_payment(claim["claim_number"], paid=120.01)
    expect(claims.field_error("paid")).to_have_text("Paid + adjustment cannot exceed the outstanding balance")

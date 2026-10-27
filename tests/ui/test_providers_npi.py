"""Provider onboarding & NPI validation — manual suite TS-03."""
import pytest
from playwright.sync_api import Page, expect

from pages.providers_page import ProvidersPage
from utils.data_loader import cases


@pytest.fixture
def providers(logged_in_page: Page) -> ProvidersPage:
    return ProvidersPage(logged_in_page).open()


@pytest.mark.ui
@pytest.mark.regression
@pytest.mark.defect
@pytest.mark.parametrize("case", cases("npi", "npi_cases"))
def test_npi_inline_validation_boundaries(providers: ProvidersPage, case):
    """Regression guard for the NPI boundary-value defect cluster (9/10/11 digits, check digit)."""
    providers.check_npi(case["npi"])
    expected = "✔ Valid NPI" if case["valid"] else f"✖ {case['reason']}"
    expect(providers.npi_status).to_have_text(expected)


@pytest.mark.ui
@pytest.mark.smoke
def test_add_provider_with_valid_npi(providers: ProvidersPage):
    providers.add("Anita", "Desai", "1456789019", "Pediatrics")
    providers.expect_toast("Provider added: Dr. Anita Desai")
    expect(providers.row("1456789019")).to_contain_text("Pediatrics")


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_add_provider_rejects_bad_check_digit(providers: ProvidersPage):
    providers.add("Bad", "Digit", "1234567890")
    expect(providers.field_error("npi")).to_have_text("NPI check digit is invalid")
    expect(providers.rows).to_have_count(2)


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_duplicate_npi_rejected(providers: ProvidersPage):
    providers.add("Clone", "Smith", "1234567893")
    expect(providers.field_error("npi")).to_have_text("A provider with this NPI already exists")

"""Encounter capture & provider dashboard — manual suites TS-04 / TS-05."""
import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.dashboard_page import ProviderDashboardPage
from pages.encounters_page import EncountersPage
from pages.login_page import LoginPage
from utils.data_factory import days_ago, days_ahead
from utils.data_loader import cases

EMILY = "Emily Carter (MRN000100)"
DR_SMITH = "Dr. John Smith"


@pytest.fixture
def encounters(logged_in_page: Page) -> EncountersPage:
    return EncountersPage(logged_in_page).open()


@pytest.mark.ui
@pytest.mark.smoke
def test_create_encounter_with_multiple_lines(encounters: EncountersPage):
    encounters.fill(EMILY, DR_SMITH, days_ago(2), "I10, E11.9", [("99214", 1), ("93000", 1), ("36415", 2)])
    expect(encounters.total_charge).to_have_text("$244.00")   # 175 + 45 + 2×12
    encounters.save()
    encounters.expect_toast("— $244.00")
    expect(encounters.rows).to_have_count(1)
    expect(encounters.rows.first).to_contain_text("I10, E11.9")


@pytest.mark.ui
@pytest.mark.regression
def test_total_charge_recalculates_live(encounters: EncountersPage):
    encounters.set_line(0, "99213", 1)
    expect(encounters.total_charge).to_have_text("$120.00")
    encounters.set_line(0, "99213", 3)
    expect(encounters.total_charge).to_have_text("$360.00")


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize("dos, error", [
    ("future", "Date of service cannot be in the future"),
    ("1980-01-01", "Date of service cannot be before the patient's date of birth"),
], ids=["future-dos", "dos-before-dob"])
def test_date_of_service_rules(encounters: EncountersPage, dos, error):
    encounters.fill(EMILY, DR_SMITH, days_ahead(1) if dos == "future" else dos, "I10", [("99213", 1)])
    encounters.save()
    expect(encounters.field_error("date_of_service")).to_have_text(error)


@pytest.mark.ui
@pytest.mark.regression
@pytest.mark.parametrize("case", cases("patients", "icd10_codes"))
def test_icd10_format_validation(encounters: EncountersPage, case):
    encounters.fill(EMILY, DR_SMITH, days_ago(1), case["code"], [("99213", 1)])
    encounters.save()
    if case["valid"]:
        encounters.expect_toast("saved")
        expect(encounters.field_error("diagnoses")).to_have_text("")
    else:
        expect(encounters.field_error("diagnoses")).to_have_text(f"'{case['code'].upper()}' is not a valid ICD-10-CM code")


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_encounter_requires_diagnosis_and_procedure(encounters: EncountersPage):
    encounters.fill(EMILY, DR_SMITH, days_ago(1), "")
    encounters.save()
    expect(encounters.field_error("diagnoses")).to_have_text("At least one ICD-10 diagnosis code is required")
    encounters.diagnoses.fill("I10")
    encounters.save()
    expect(encounters.field_error("lines")).to_have_text("At least one procedure (CPT) line is required")


@pytest.mark.ui
@pytest.mark.smoke
@pytest.mark.defect
def test_new_encounter_appears_on_provider_dashboard(page: Page, api):
    """Regression guard: encounter details were missing from the provider dashboard."""
    enc = api.post("/api/encounters", data={
        "patient_id": 101, "provider_id": 1, "date_of_service": days_ago(1),
        "diagnoses": ["R07.9"], "lines": [{"cpt": "99214", "units": 1}, {"cpt": "93000", "units": 1}]}).json()

    login = LoginPage(page).open()
    login.login(*settings.provider)
    dashboard = ProviderDashboardPage(page)
    expect(dashboard.provider_name).to_have_text("Dr. John Smith — Cardiology")
    row = dashboard.encounter_row(enc["id"])
    expect(row.get_by_test_id("patient")).to_have_text("Michael Nguyen")
    expect(row.get_by_test_id("dx")).to_have_text("R07.9")
    expect(row.get_by_test_id("cpt")).to_have_text("99214, 93000")
    expect(row.get_by_test_id("charge")).to_have_text("$220.00")
    expect(dashboard.kpi_encounters).to_have_text("1")
    expect(dashboard.kpi_charges).to_have_text("$220.00")


@pytest.mark.ui
@pytest.mark.regression
def test_provider_sees_only_own_encounters(page: Page, api):
    api.post("/api/encounters", data={"patient_id": 100, "provider_id": 2, "date_of_service": days_ago(1),
                                      "diagnoses": ["J06.9"], "lines": [{"cpt": "99213", "units": 1}]})
    login = LoginPage(page).open()
    login.login(*settings.provider)
    dashboard = ProviderDashboardPage(page)
    expect(dashboard.provider_name).to_be_visible()
    expect(dashboard.empty_state).to_be_visible()
    expect(dashboard.kpi_encounters).to_have_text("0")

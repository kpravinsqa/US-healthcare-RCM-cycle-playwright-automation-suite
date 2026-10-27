"""Patient registration & search — manual suite TS-02."""
import pytest
from playwright.sync_api import Page, expect

from pages.patients_page import PatientsPage
from utils import data_factory
from utils.data_loader import cases


@pytest.fixture
def patients(logged_in_page: Page) -> PatientsPage:
    return PatientsPage(logged_in_page).open()


@pytest.mark.ui
@pytest.mark.smoke
def test_register_insured_patient(patients: PatientsPage):
    data = data_factory.patient(first_name="Grace", last_name="Holloway")
    patients.register(**data)
    patients.expect_toast("Patient registered: MRN")
    patients.search("Grace Holloway")
    expect(patients.rows).to_have_count(1)
    expect(patients.rows.first).to_contain_text(data["member_id"])


@pytest.mark.ui
@pytest.mark.regression
def test_register_self_pay_patient_without_member_id(patients: PatientsPage):
    patients.register(**data_factory.patient(first_name="Leo", last_name="Self", payer="Self-Pay"))
    patients.expect_toast("Patient registered")
    expect(patients.member_id).to_be_enabled()  # form reset afterwards


@pytest.mark.ui
@pytest.mark.regression
def test_member_id_disabled_for_self_pay(patients: PatientsPage):
    patients.payer.select_option("Self-Pay")
    expect(patients.member_id).to_be_disabled()


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize("case", cases("patients", "invalid_patients"))
def test_registration_field_validation(patients: PatientsPage, case):
    override = dict(case["override"])
    if override.get("dob") == "+1":
        override["dob"] = data_factory.days_ahead(1)
    patients.register(**data_factory.patient(**override))
    expect(patients.field_error(case["field"])).to_have_text(case["error"])


@pytest.mark.ui
@pytest.mark.negative
@pytest.mark.regression
def test_duplicate_patient_detection(patients: PatientsPage):
    patients.register(**data_factory.patient(first_name="emily", last_name="CARTER", dob="1985-04-12"))
    expect(patients.form_error).to_have_text("Possible duplicate: patient MRN000100 has the same name and date of birth")


@pytest.mark.ui
@pytest.mark.regression
@pytest.mark.parametrize("term, expected", [("MRN000101", 1), ("carter", 1), ("a", 3), ("zzz", 0)])
def test_patient_search(patients: PatientsPage, term, expected):
    patients.search(term)
    expect(patients.rows).to_have_count(expected)
    if expected == 0:
        expect(patients.no_results).to_be_visible()

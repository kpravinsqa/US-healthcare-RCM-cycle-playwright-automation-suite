import pytest

from api.rcm_client import RcmClient
from utils import data_factory
from utils.data_loader import cases


@pytest.fixture
def rcm(api) -> RcmClient:
    return RcmClient(api)


@pytest.mark.api
@pytest.mark.regression
@pytest.mark.parametrize("case", cases("npi", "npi_cases"))
def test_npi_validation_endpoint(rcm, case):
    body = rcm.validate_npi(case["npi"]).json()
    assert body == {"npi": case["npi"], "valid": case["valid"], "reason": case["reason"]}


@pytest.mark.api
@pytest.mark.smoke
def test_create_patient_assigns_sequential_mrn(rcm):
    resp = rcm.create_patient(**data_factory.patient())
    assert resp.status == 201
    body = resp.json()
    assert body["mrn"] == f"MRN{body['id']:06d}"


@pytest.mark.api
@pytest.mark.negative
@pytest.mark.regression
def test_unauthenticated_access_blocked(anon_api):
    assert anon_api.get("/api/patients").status == 401


@pytest.mark.api
@pytest.mark.negative
@pytest.mark.regression
def test_front_desk_cannot_call_claims_api(playwright, base_url):
    ctx = playwright.request.new_context(base_url=base_url)
    token = ctx.post("/api/auth/login", data={"username": "front_desk", "password": "Health@123"}).json()["token"]
    resp = ctx.get("/api/claims", headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 403
    assert resp.json()["error"] == "You do not have permission to access this module"
    ctx.dispose()


@pytest.mark.api
@pytest.mark.regression
def test_encounter_charge_uses_fee_schedule(rcm):
    enc = rcm.create_encounter(lines=(("99203", 1), ("85025", 2), ("36415", 1))).json()
    assert enc["total_charge"] == 150.00 + 2 * 28.00 + 12.00
    assert enc["status"] == "OPEN"


@pytest.mark.api
@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize("lines, error", [
    ((("99999", 1),), "CPT 99999 is not in the fee schedule"),
    ((("99213", 0),), "Units must be between 1 and 99"),
    ((("99213", 100),), "Units must be between 1 and 99"),
], ids=["unknown-cpt", "units-0", "units-100"])
def test_encounter_line_validation(rcm, lines, error):
    resp = rcm.create_encounter(lines=lines)
    assert resp.status == 400
    assert resp.json() == {"error": error, "field": "lines"}


@pytest.mark.api
@pytest.mark.defect
@pytest.mark.regression
def test_dashboard_summary_matches_encounters(rcm):
    a = rcm.create_encounter(lines=(("99214", 1),)).json()
    rcm.create_encounter(patient_id=101, lines=(("99213", 1), ("93000", 1))).json()
    rcm.create_claim(a["id"])
    dash = rcm.dashboard(provider_id=1).json()
    assert dash["summary"] == {"encounters": 2, "open": 1, "billed": 1, "total_charges": 340.00}
    assert {e["id"] for e in dash["encounters"]} >= {a["id"]}
    for e in dash["encounters"]:
        assert e["patient_name"] and e["diagnoses"] and e["lines"], "encounter details must be populated"


@pytest.mark.api
@pytest.mark.regression
def test_claim_cannot_be_created_twice(rcm):
    enc = rcm.create_encounter().json()
    assert rcm.create_claim(enc["id"]).status == 201
    resp = rcm.create_claim(enc["id"])
    assert resp.status == 409


@pytest.mark.api
@pytest.mark.negative
@pytest.mark.regression
def test_payment_on_draft_claim_rejected(rcm):
    claim = rcm.create_claim(rcm.create_encounter().json()["id"]).json()
    resp = rcm.post_payment(claim["id"], 10)
    assert resp.status == 409


@pytest.mark.api
@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize("paid, adjustment, field", [(-1, 0, "paid"), (10, -5, "adjustment"), ("10", 0, "paid")])
def test_payment_amount_validation(rcm, paid, adjustment, field):
    claim = rcm.create_claim(rcm.create_encounter().json()["id"]).json()
    rcm.submit_claim(claim["id"])
    resp = rcm.post_payment(claim["id"], paid, adjustment)
    assert resp.status == 400
    assert resp.json()["field"] == field

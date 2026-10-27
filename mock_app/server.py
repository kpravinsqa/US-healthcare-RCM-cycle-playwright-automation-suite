"""
Mock US-healthcare Revenue Cycle Management (RCM) web application.

Synthetic re-creation of the flows exercised while testing a provider-side RCM
product: patient registration, provider onboarding with NPI validation,
encounter capture (CPT / ICD-10), the provider dashboard, claim creation,
claim scrubbing / submission and payment posting.

All patients and providers are fictitious. No PHI and no proprietary code.
"""
from __future__ import annotations

import copy
import itertools
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from mock_app.core import ApiError, App, require

app = App(Path(__file__).parent / "static")

TIMELY_FILING_DAYS = 365
ICD10 = re.compile(r"^[A-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")
PHONE = re.compile(r"^\d{10}$")
ZIP = re.compile(r"^\d{5}$")
MEMBER_ID = re.compile(r"^[A-Za-z0-9]{6,15}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

FEE_SCHEDULE = {
    "99203": {"description": "New patient office visit, low complexity", "fee": 150.00},
    "99213": {"description": "Established patient office visit, low complexity", "fee": 120.00},
    "99214": {"description": "Established patient office visit, moderate complexity", "fee": 175.00},
    "93000": {"description": "Electrocardiogram, complete", "fee": 45.00},
    "85025": {"description": "Complete blood count with differential", "fee": 28.00},
    "36415": {"description": "Routine venipuncture", "fee": 12.00},
}
PAYERS = ["Aetna", "BlueCross BlueShield", "Cigna", "Medicare", "UnitedHealthcare", "Self-Pay"]

USERS_SEED = {
    "billing_admin": {"password": "Health@123", "display_name": "Billing Admin", "role": "ADMIN", "provider_id": None},
    "front_desk": {"password": "Health@123", "display_name": "Front Desk", "role": "FRONT_DESK", "provider_id": None},
    "dr_smith": {"password": "Health@123", "display_name": "Dr. John Smith", "role": "PROVIDER", "provider_id": 1},
}
ROLE_ACCESS = {
    "ADMIN": {"patients", "providers", "encounters", "claims", "dashboard"},
    "FRONT_DESK": {"patients", "encounters"},
    "PROVIDER": {"dashboard", "encounters", "patients"},
}

STATE: dict = {}
_ids = itertools.count(1)


def today() -> date:
    return date.today()


def reset() -> None:
    global _ids
    _ids = itertools.count(100)
    app.revoke_all_tokens()
    STATE.clear()
    STATE["users"] = copy.deepcopy(USERS_SEED)
    STATE["providers"] = {
        1: {"id": 1, "first_name": "John", "last_name": "Smith", "npi": "1234567893", "specialty": "Cardiology"},
        2: {"id": 2, "first_name": "Priya", "last_name": "Rao", "npi": "1987654328", "specialty": "Family Medicine"},
    }
    STATE["patients"] = {}
    for p in [
        dict(first_name="Emily", last_name="Carter", dob="1985-04-12", gender="F", phone="5125550101",
             email="emily.carter@example.com", zip="78701", payer="Aetna", member_id="AET123456"),
        dict(first_name="Michael", last_name="Nguyen", dob="1972-11-30", gender="M", phone="5125550102",
             email="m.nguyen@example.com", zip="78702", payer="Medicare", member_id="1EG4TE5MK73"),
        dict(first_name="Sofia", last_name="Martinez", dob="1999-07-08", gender="F", phone="5125550103",
             email="", zip="78703", payer="Self-Pay", member_id=""),
    ]:
        _store_patient(p)
    STATE["encounters"] = {}
    STATE["claims"] = {}


def _store_patient(data: dict) -> dict:
    pid = next(_ids)
    patient = {"id": pid, "mrn": f"MRN{pid:06d}", **data}
    STATE["patients"][pid] = patient
    return patient


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def npi_is_valid(npi: str) -> bool:
    """CMS NPI check digit: Luhn over '80840' + first 9 digits."""
    if not re.fullmatch(r"\d{10}", npi or ""):
        return False
    total = 0
    for i, ch in enumerate(reversed("80840" + npi)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            d = d - 9 if d > 9 else d
        total += d
    return total % 10 == 0


def access(req, area: str):
    if area not in ROLE_ACCESS[req.user["role"]]:
        raise ApiError(403, "You do not have permission to access this module")


def parse_date(value, field, label):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ApiError(400, f"{label} must be a valid date (YYYY-MM-DD)", field=field)


# --------------------------------------------------------------------------- test hooks / auth
@app.route("POST", "/api/test/reset", auth=False)
def _reset(req):
    reset()
    return {"status": "reset"}


@app.route("POST", "/api/auth/login", auth=False)
def login(req):
    username = require(req.body, "username", "Username")
    password = require(req.body, "password", "Password", strip=False)
    user = STATE["users"].get(username)
    if not user or user["password"] != password:
        raise ApiError(401, "Invalid username or password")
    profile = {"username": username, "display_name": user["display_name"], "role": user["role"],
               "provider_id": user["provider_id"]}
    return {"token": app.issue_token(profile), "user": profile}


@app.route("GET", "/api/reference")
def reference(req):
    return {"payers": PAYERS, "fee_schedule": FEE_SCHEDULE, "timely_filing_days": TIMELY_FILING_DAYS}


# --------------------------------------------------------------------------- patients
def validate_patient(body: dict) -> dict:
    data = {
        "first_name": require(body, "first_name", "First name"),
        "last_name": require(body, "last_name", "Last name"),
        "gender": require(body, "gender", "Gender"),
        "phone": require(body, "phone", "Phone"),
        "zip": require(body, "zip", "ZIP code"),
        "payer": require(body, "payer", "Payer"),
        "email": (body.get("email") or "").strip(),
        "member_id": (body.get("member_id") or "").strip(),
    }
    dob = parse_date(require(body, "dob", "Date of birth"), "dob", "Date of birth")
    if dob > today():
        raise ApiError(400, "Date of birth cannot be in the future", field="dob")
    if (today() - dob).days > 120 * 365.25:
        raise ApiError(400, "Date of birth cannot be more than 120 years ago", field="dob")
    data["dob"] = dob.isoformat()
    for name in ("first_name", "last_name"):
        if not re.fullmatch(r"[A-Za-z][A-Za-z '\-]{0,49}", data[name]):
            raise ApiError(400, f"{name.replace('_', ' ').capitalize()} may contain letters, spaces, ' and - only", field=name)
    if data["gender"] not in ("M", "F", "U"):
        raise ApiError(400, "Gender must be M, F or U", field="gender")
    if not PHONE.match(data["phone"]):
        raise ApiError(400, "Phone must be 10 digits", field="phone")
    if not ZIP.match(data["zip"]):
        raise ApiError(400, "ZIP code must be 5 digits", field="zip")
    if data["email"] and not EMAIL.match(data["email"]):
        raise ApiError(400, "Enter a valid email address", field="email")
    if data["payer"] not in PAYERS:
        raise ApiError(400, "Unknown payer", field="payer")
    if data["payer"] != "Self-Pay" and not MEMBER_ID.match(data["member_id"]):
        raise ApiError(400, "Member ID must be 6-15 letters or digits", field="member_id")
    return data


@app.route("GET", "/api/patients")
def list_patients(req):
    access(req, "patients")
    q = (req.query.get("q") or "").strip().lower()
    items = [p for p in STATE["patients"].values()
             if not q or q in f"{p['first_name']} {p['last_name']}".lower() or q == p["mrn"].lower()]
    return {"count": len(items), "items": items}


@app.route("POST", "/api/patients")
def create_patient(req):
    access(req, "patients")
    data = validate_patient(req.body)
    for p in STATE["patients"].values():
        if (p["first_name"].lower(), p["last_name"].lower(), p["dob"]) == \
                (data["first_name"].lower(), data["last_name"].lower(), data["dob"]):
            raise ApiError(409, f"Possible duplicate: patient {p['mrn']} has the same name and date of birth")
    return 201, _store_patient(data)


@app.route("GET", r"/api/patients/(?P<pid>\d+)")
def get_patient(req):
    access(req, "patients")
    p = STATE["patients"].get(int(req.params["pid"]))
    if not p:
        raise ApiError(404, "Patient not found")
    return p


# --------------------------------------------------------------------------- providers
@app.route("GET", "/api/providers")
def list_providers(req):
    return {"items": list(STATE["providers"].values())}


@app.route("GET", r"/api/npi/(?P<npi>[^/]+)/validate")
def validate_npi(req):
    npi = req.params["npi"]
    if not re.fullmatch(r"\d+", npi):
        return {"npi": npi, "valid": False, "reason": "NPI must contain digits only"}
    if len(npi) != 10:
        return {"npi": npi, "valid": False, "reason": "NPI must be exactly 10 digits"}
    if not npi_is_valid(npi):
        return {"npi": npi, "valid": False, "reason": "NPI check digit is invalid"}
    return {"npi": npi, "valid": True, "reason": None}


@app.route("POST", "/api/providers")
def create_provider(req):
    access(req, "providers")
    first = require(req.body, "first_name", "First name")
    last = require(req.body, "last_name", "Last name")
    specialty = require(req.body, "specialty", "Specialty")
    npi = str(require(req.body, "npi", "NPI"))
    verdict = validate_npi(type("R", (), {"params": {"npi": npi}})())
    if not verdict["valid"]:
        raise ApiError(400, verdict["reason"], field="npi")
    if any(p["npi"] == npi for p in STATE["providers"].values()):
        raise ApiError(409, "A provider with this NPI already exists", field="npi")
    pid = next(_ids)
    provider = {"id": pid, "first_name": first, "last_name": last, "npi": npi, "specialty": specialty}
    STATE["providers"][pid] = provider
    return 201, provider


# --------------------------------------------------------------------------- encounters
def _encounter_view(e):
    patient = STATE["patients"][e["patient_id"]]
    provider = STATE["providers"][e["provider_id"]]
    return {**e, "patient_name": f"{patient['first_name']} {patient['last_name']}", "mrn": patient["mrn"],
            "provider_name": f"Dr. {provider['first_name']} {provider['last_name']}",
            "total_charge": round(sum(FEE_SCHEDULE[l["cpt"]]["fee"] * l["units"] for l in e["lines"]), 2)}


@app.route("POST", "/api/encounters")
def create_encounter(req):
    access(req, "encounters")
    b = req.body
    patient = STATE["patients"].get(b.get("patient_id"))
    if not patient:
        raise ApiError(400, "Select a valid patient", field="patient_id")
    if b.get("provider_id") not in STATE["providers"]:
        raise ApiError(400, "Select a valid rendering provider", field="provider_id")
    dos = parse_date(require(b, "date_of_service", "Date of service"), "date_of_service", "Date of service")
    if dos > today():
        raise ApiError(400, "Date of service cannot be in the future", field="date_of_service")
    if dos < date.fromisoformat(patient["dob"]):
        raise ApiError(400, "Date of service cannot be before the patient's date of birth", field="date_of_service")
    diagnoses = [d.strip().upper() for d in b.get("diagnoses") or [] if d and d.strip()]
    if not diagnoses:
        raise ApiError(400, "At least one ICD-10 diagnosis code is required", field="diagnoses")
    for d in diagnoses:
        if not ICD10.match(d):
            raise ApiError(400, f"'{d}' is not a valid ICD-10-CM code", field="diagnoses")
    lines = []
    for line in b.get("lines") or []:
        cpt = str(line.get("cpt", "")).strip()
        units = line.get("units", 1)
        if cpt not in FEE_SCHEDULE:
            raise ApiError(400, f"CPT {cpt or '(blank)'} is not in the fee schedule", field="lines")
        if not isinstance(units, int) or not 1 <= units <= 99:
            raise ApiError(400, "Units must be between 1 and 99", field="lines")
        lines.append({"cpt": cpt, "units": units})
    if not lines:
        raise ApiError(400, "At least one procedure (CPT) line is required", field="lines")
    eid = next(_ids)
    enc = {"id": eid, "patient_id": patient["id"], "provider_id": b["provider_id"], "date_of_service": dos.isoformat(),
           "diagnoses": diagnoses, "lines": lines, "status": "OPEN", "created_at": now()}
    STATE["encounters"][eid] = enc
    return 201, _encounter_view(enc)


@app.route("GET", "/api/encounters")
def list_encounters(req):
    access(req, "encounters")
    items = [_encounter_view(e) for e in STATE["encounters"].values()]
    return {"count": len(items), "items": sorted(items, key=lambda e: e["id"], reverse=True)}


@app.route("GET", "/api/dashboard/provider")
def provider_dashboard(req):
    """Encounters for the logged-in provider (or ?provider_id= for admins)."""
    access(req, "dashboard")
    pid = req.user["provider_id"] or int(req.query.get("provider_id") or 0)
    if pid not in STATE["providers"]:
        raise ApiError(400, "provider_id is required")
    mine = [_encounter_view(e) for e in STATE["encounters"].values() if e["provider_id"] == pid]
    return {
        "provider": STATE["providers"][pid],
        "summary": {"encounters": len(mine), "open": sum(e["status"] == "OPEN" for e in mine),
                    "billed": sum(e["status"] == "BILLED" for e in mine),
                    "total_charges": round(sum(e["total_charge"] for e in mine), 2)},
        "encounters": sorted(mine, key=lambda e: e["date_of_service"], reverse=True),
    }


# --------------------------------------------------------------------------- claims
def _claim_view(c):
    enc = _encounter_view(STATE["encounters"][c["encounter_id"]])
    paid = round(sum(p["paid"] for p in c["payments"]), 2)
    adjusted = round(sum(p["adjustment"] for p in c["payments"]), 2)
    return {**c, "patient_name": enc["patient_name"], "mrn": enc["mrn"], "date_of_service": enc["date_of_service"],
            "paid_amount": paid, "adjustment_amount": adjusted,
            "outstanding_balance": round(c["billed_amount"] - paid - adjusted, 2)}


@app.route("POST", "/api/claims")
def create_claim(req):
    access(req, "claims")
    enc = STATE["encounters"].get(req.body.get("encounter_id"))
    if not enc:
        raise ApiError(400, "Select a valid encounter", field="encounter_id")
    if enc["status"] != "OPEN":
        raise ApiError(409, "A claim already exists for this encounter")
    patient = STATE["patients"][enc["patient_id"]]
    cid = next(_ids)
    claim = {"id": cid, "claim_number": f"CLM-{cid:07d}", "encounter_id": enc["id"], "payer": patient["payer"],
             "member_id": patient["member_id"], "billed_amount": _encounter_view(enc)["total_charge"],
             "status": "DRAFT", "payments": [], "created_at": now(), "scrub_errors": []}
    STATE["claims"][cid] = claim
    enc["status"] = "BILLED"
    return 201, _claim_view(claim)


@app.route("GET", "/api/claims")
def list_claims(req):
    access(req, "claims")
    items = [_claim_view(c) for c in STATE["claims"].values()]
    return {"count": len(items), "items": sorted(items, key=lambda c: c["id"], reverse=True)}


def _claim(req):
    access(req, "claims")
    c = STATE["claims"].get(int(req.params["cid"]))
    if not c:
        raise ApiError(404, "Claim not found")
    return c


@app.route("POST", r"/api/claims/(?P<cid>\d+)/submit")
def submit_claim(req):
    c = _claim(req)
    if c["status"] != "DRAFT":
        raise ApiError(409, f"Only DRAFT claims can be submitted (status: {c['status']})")
    errors = []
    if c["payer"] == "Self-Pay":
        errors.append("Self-pay encounters are billed to the patient, not submitted to a payer")
    dos = date.fromisoformat(STATE["encounters"][c["encounter_id"]]["date_of_service"])
    if (today() - dos).days > TIMELY_FILING_DAYS:
        errors.append(f"Timely filing limit exceeded ({TIMELY_FILING_DAYS} days from date of service)")
    c["scrub_errors"] = errors
    if errors:
        c["status"] = "REJECTED"
        raise ApiError(422, "; ".join(errors))
    c["status"] = "SUBMITTED"
    c["submitted_at"] = now()
    return _claim_view(c)


@app.route("POST", r"/api/claims/(?P<cid>\d+)/payments")
def post_payment(req):
    c = _claim(req)
    if c["status"] not in ("SUBMITTED", "PARTIALLY_PAID"):
        raise ApiError(409, "Payments can only be posted to submitted claims")
    paid, adj = req.body.get("paid"), req.body.get("adjustment", 0)
    for val, field in ((paid, "paid"), (adj, "adjustment")):
        if not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0:
            raise ApiError(400, f"{field.capitalize()} amount must be zero or more", field=field)
    view = _claim_view(c)
    if round(paid + adj, 2) > view["outstanding_balance"]:
        raise ApiError(400, "Paid + adjustment cannot exceed the outstanding balance", field="paid")
    c["payments"].append({"paid": round(paid, 2), "adjustment": round(adj, 2), "posted_at": now()})
    balance = _claim_view(c)["outstanding_balance"]
    c["status"] = "PAID" if balance == 0 else "PARTIALLY_PAID"
    return _claim_view(c)


def create_server(host: str = "127.0.0.1", port: int = 0):
    reset()
    return app.create_server(host, port)


if __name__ == "__main__":
    srv = create_server("127.0.0.1", 8000)
    print("Mock RCM app at http://127.0.0.1:8000  (billing_admin / Health@123)")
    srv.serve_forever()

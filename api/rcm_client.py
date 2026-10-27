"""Service object for the RCM REST API."""
from datetime import date, timedelta

from playwright.sync_api import APIRequestContext


class RcmClient:
    def __init__(self, ctx: APIRequestContext):
        self.ctx = ctx

    def patients(self, q=""):
        return self.ctx.get("/api/patients", params={"q": q})

    def create_patient(self, **data):
        return self.ctx.post("/api/patients", data=data)

    def validate_npi(self, npi: str):
        return self.ctx.get(f"/api/npi/{npi}/validate")

    def create_provider(self, **data):
        return self.ctx.post("/api/providers", data=data)

    def create_encounter(self, patient_id=100, provider_id=1, dos=None, diagnoses=("I10",), lines=(("99213", 1),)):
        dos = dos or (date.today() - timedelta(days=3)).isoformat()
        return self.ctx.post("/api/encounters", data={
            "patient_id": patient_id, "provider_id": provider_id, "date_of_service": dos,
            "diagnoses": list(diagnoses), "lines": [{"cpt": c, "units": u} for c, u in lines]})

    def dashboard(self, provider_id=None):
        return self.ctx.get("/api/dashboard/provider", params={"provider_id": provider_id} if provider_id else None)

    def create_claim(self, encounter_id):
        return self.ctx.post("/api/claims", data={"encounter_id": encounter_id})

    def submit_claim(self, claim_id):
        return self.ctx.post(f"/api/claims/{claim_id}/submit")

    def post_payment(self, claim_id, paid, adjustment=0):
        return self.ctx.post(f"/api/claims/{claim_id}/payments", data={"paid": paid, "adjustment": adjustment})

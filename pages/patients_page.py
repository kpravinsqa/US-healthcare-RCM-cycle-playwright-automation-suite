from playwright.sync_api import Page

from pages.base_page import BasePage


class PatientsPage(BasePage):
    path = "/patients.html"
    FIELDS = ("first_name", "last_name", "dob", "phone", "email", "zip", "member_id")

    def __init__(self, page: Page):
        super().__init__(page)
        self.form = page.locator("#patient-form")
        self.gender = page.get_by_test_id("gender")
        self.payer = page.get_by_test_id("payer")
        self.member_id = page.get_by_test_id("member_id")
        self.register_button = page.get_by_test_id("register-patient")
        self.form_error = page.get_by_test_id("error-form")
        self.search_input = page.get_by_test_id("patient-search")
        self.search_button = page.get_by_test_id("search-button")
        self.rows = page.get_by_test_id("patients-table").locator("tbody tr")
        self.no_results = page.get_by_test_id("no-patients")

    def open(self):
        super().open()
        self.payer.locator("option", has_text="Aetna").wait_for(state="attached")
        return self

    def register(self, **patient):
        for name in self.FIELDS:
            if name in patient and not (name == "member_id" and patient.get("payer") == "Self-Pay"):
                self.form.get_by_test_id(name).fill(patient[name])
        if "gender" in patient:
            self.gender.select_option(patient["gender"])
        if "payer" in patient:
            self.payer.select_option(patient["payer"])
            if patient["payer"] != "Self-Pay" and "member_id" in patient:
                self.member_id.fill(patient["member_id"])
        self.register_button.click()

    def search(self, term: str):
        self.search_input.fill(term)
        with self.page.expect_response("**/api/patients?q=*"):
            self.search_button.click()

    def row(self, mrn: str):
        return self.page.get_by_test_id(f"patient-{mrn}")

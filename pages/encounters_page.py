from playwright.sync_api import Page

from pages.base_page import BasePage


class EncountersPage(BasePage):
    path = "/encounters.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.patient = page.get_by_test_id("patient")
        self.provider = page.get_by_test_id("provider")
        self.date_of_service = page.get_by_test_id("date_of_service")
        self.diagnoses = page.get_by_test_id("diagnoses")
        self.add_line_button = page.get_by_test_id("add-line")
        self.total_charge = page.get_by_test_id("total-charge")
        self.save_button = page.get_by_test_id("save-encounter")
        self.rows = page.get_by_test_id("encounters-table").locator("tbody tr")

    def open(self):
        super().open()
        self.page.get_by_test_id("cpt-0").wait_for()
        return self

    def set_line(self, index: int, cpt: str, units: int = 1):
        if index > 0 and self.page.get_by_test_id(f"cpt-{index}").count() == 0:
            self.add_line_button.click()
        self.page.get_by_test_id(f"cpt-{index}").select_option(cpt)
        self.page.get_by_test_id(f"units-{index}").fill(str(units))

    def fill(self, patient_label=None, provider_label=None, dos=None, diagnoses=None, lines=()):
        if patient_label:
            self.patient.select_option(label=patient_label)
        if provider_label:
            self.provider.select_option(label=provider_label)
        if dos:
            self.date_of_service.fill(dos)
        if diagnoses is not None:
            self.diagnoses.fill(diagnoses)
        for i, (cpt, units) in enumerate(lines):
            self.set_line(i, cpt, units)

    def save(self):
        self.save_button.click()

from playwright.sync_api import Page

from pages.base_page import BasePage


class ProvidersPage(BasePage):
    path = "/providers.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.first_name = page.get_by_test_id("first_name")
        self.last_name = page.get_by_test_id("last_name")
        self.npi = page.get_by_test_id("npi")
        self.npi_status = page.get_by_test_id("npi-status")
        self.specialty = page.get_by_test_id("specialty")
        self.add_button = page.get_by_test_id("add-provider")
        self.rows = page.get_by_test_id("providers-table").locator("tbody tr")

    def check_npi(self, npi: str):
        self.npi.fill(npi)
        with self.page.expect_response("**/api/npi/**"):
            self.npi.blur()

    def add(self, first: str, last: str, npi: str, specialty: str = "Internal Medicine"):
        self.first_name.fill(first)
        self.last_name.fill(last)
        self.npi.fill(npi)
        self.specialty.select_option(specialty)
        self.add_button.click()

    def row(self, npi: str):
        return self.page.get_by_test_id(f"provider-{npi}")

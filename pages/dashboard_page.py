from playwright.sync_api import Page

from pages.base_page import BasePage


class ProviderDashboardPage(BasePage):
    path = "/dashboard.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.provider_name = page.get_by_test_id("provider-name")
        self.provider_select = page.get_by_test_id("provider-select")
        self.kpi_encounters = page.get_by_test_id("kpi-encounters")
        self.kpi_open = page.get_by_test_id("kpi-open")
        self.kpi_billed = page.get_by_test_id("kpi-billed")
        self.kpi_charges = page.get_by_test_id("kpi-charges")
        self.rows = page.get_by_test_id("dashboard-encounters").locator("tbody tr")
        self.empty_state = page.get_by_test_id("no-encounters")

    def encounter_row(self, encounter_id: int):
        return self.page.get_by_test_id(f"dash-encounter-{encounter_id}")

from playwright.sync_api import Page

from pages.base_page import BasePage


class ClaimsPage(BasePage):
    path = "/claims.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.encounter_select = page.get_by_test_id("encounter-select")
        self.create_button = page.get_by_test_id("create-claim")
        self.rows = page.get_by_test_id("claims-table").locator("tbody tr")
        self.payment_panel = page.get_by_test_id("payment-panel")
        self.paid = page.get_by_test_id("paid-amount")
        self.adjustment = page.get_by_test_id("adjustment-amount")
        self.post_button = page.get_by_test_id("post-payment")

    def open(self):
        super().open()
        self.encounter_select.locator("option").first.wait_for(state="attached")
        return self

    def create_for(self, encounter_id: int):
        self.encounter_select.select_option(str(encounter_id))
        self.create_button.click()

    def row(self, claim_number: str):
        return self.page.get_by_test_id(f"claim-{claim_number}")

    def cell(self, claim_number: str, name: str):
        return self.row(claim_number).get_by_test_id(name)

    def submit(self, claim_number: str):
        self.page.get_by_test_id(f"submit-{claim_number}").click()

    def post_payment(self, claim_number: str, paid: float, adjustment: float = 0):
        self.page.get_by_test_id(f"pay-{claim_number}").click()
        self.paid.fill(str(paid))
        self.adjustment.fill(str(adjustment))
        self.post_button.click()

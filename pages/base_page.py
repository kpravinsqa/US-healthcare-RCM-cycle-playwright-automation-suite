from playwright.sync_api import Locator, Page, expect


class BasePage:
    """Common behaviour shared by every page object."""

    path: str = "/"

    def __init__(self, page: Page):
        self.page = page
        self.toast: Locator = page.get_by_test_id("toast")
        self.user_badge: Locator = page.get_by_test_id("user-badge")
        self.logout_button: Locator = page.get_by_test_id("logout")

    def open(self):
        self.page.goto(self.path)
        return self

    def nav_to(self, test_id: str):
        self.page.get_by_test_id(f"nav-{test_id}").click()

    def expect_toast(self, text: str):
        expect(self.toast).to_contain_text(text)

    def field_error(self, field: str) -> Locator:
        return self.page.get_by_test_id(f"error-{field}")

    def logout(self):
        self.logout_button.click()
        self.page.wait_for_url("**/login.html")

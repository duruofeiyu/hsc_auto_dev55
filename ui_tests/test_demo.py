from playwright.sync_api import Page, expect

def test_local(page: Page):
    page.goto("http://localhost:8765/test.html")
    expect(page.locator("h1")).to_have_text("Hello Playwright")

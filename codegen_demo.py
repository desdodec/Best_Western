import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.bestwestern.co.uk/destinations")
    page.get_by_role("button", name="Allow all").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Show more").click()
    page.get_by_role("link", name="Hotels in Aberdeen City").click()
    page.goto("https://www.bestwestern.co.uk/destinations")
    page.get_by_role("link", name="Hotels in Aberdeenshire").click()
    page.goto("https://www.bestwestern.co.uk/destinations")
    page.get_by_role("link", name="Hotels in Anglesey").click()
    page.goto("https://www.bestwestern.co.uk/destinations")
    page.get_by_role("link", name="Hotels in Angus").click()
    page.goto("https://www.bestwestern.co.uk/destinations")
    page.get_by_role("link", name="Hotels in Argyll and Bute").click()
    page.goto("https://www.bestwestern.co.uk/destinations/argyll-and-bute")
    page.locator("div").filter(has_text=re.compile(r"^112Showing 1-59 hotels are available in Argyll and Bute$")).get_by_role("link").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)

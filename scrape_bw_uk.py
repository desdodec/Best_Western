#!/usr/bin/env python
"""
scrape_bw_uk.py

Scrapes all Best Western UK hotel addresses and writes them to hotels_uk.csv,
with debug output to help identify the correct selectors for the cookie banner
and 'Show more' buttons.
"""

import time
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.bestwestern.co.uk"
DESTINATIONS_URL = f"{BASE_URL}/destinations"
OUTPUT_CSV = "hotels_uk.csv"


# block images, fonts, stylesheets and analytics
def block_route(route, request):
    if (
        request.resource_type in ("image", "stylesheet", "font", "script")
        and "bestwestern.co.uk/hotels" not in request.url
    ):
        return route.abort()
    return route.continue_()


def accept_cookies(page):
    # 1) Try any top-level consent buttons first
    for sel in [
        "button#onetrust-accept-btn-handler",
        "button:has-text('Accept')",
        ".optanon-allow-all",
    ]:
        try:
            page.click(sel, timeout=2000)
            print(f"✅ clicked top-level cookie button via selector: {sel}")
            return
        except:
            pass

    # 2) Wait for the Cookiebot iframe to appear
    try:
        iframe_el = page.wait_for_selector(
            "iframe[src*='cookiebot.com']", timeout=10000
        )
    except Exception:
        print("⚠️ Cookiebot iframe never showed up")
        return

    # 3) Get its Frame and wait for the “Allow all” button inside
    frame = iframe_el.content_frame()
    try:
        frame.wait_for_selector(
            "button#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
            timeout=10000,
        )
        frame.click("button#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
        print("✅ clicked Cookiebot ‘Allow all’ inside iframe")
        return
    except Exception as e:
        print("⚠️ failed to click inside Cookiebot iframe:", e)

    print("⚠️ no cookie accept button found")


def expand_all_destinations(page, max_clicks=50):
    """
    Click “Show more” up to max_clicks times, then stop.
    """
    count = 0
    while count < max_clicks:
        btn = page.query_selector("a.house-button--global.x2more")
        if not btn:
            print(f"→ No more “Show more” buttons after {count} clicks.")
            return
        try:
            btn.click()
            count += 1
            print(f"→ Clicked show more #{count}")
            page.wait_for_timeout(500)  # wait 0.5s for new items to render
        except Exception as e:
            print("⚠️ Error clicking show more:", e)
            break

    print(f"→ Reached max_clicks ({max_clicks}), stopping expand.")


def get_destination_links(page):
    """
    Return a sorted, de-duplicated list of all region URLs under /destinations/,
    whether they’re written as relative paths or full absolute URLs.
    """
    anchors = page.query_selector_all("a")
    links = []
    for a in anchors:
        href = a.get_attribute("href")
        if not href:
            continue
        # skip the javascript pseudo-links
        if href.startswith("javascript"):
            continue
        # only keep ones that reference /destinations/
        if "/destinations/" not in href:
            continue

        # build a normalized absolute URL
        if href.startswith("/"):
            url = BASE_URL + href
        elif href.startswith("http"):
            url = href
        else:
            # e.g. protocol‐relative or other—skip
            continue

        # skip the main destinations page itself
        if url.rstrip("/") == DESTINATIONS_URL.rstrip("/"):
            continue

        links.append(url)

    return sorted(set(links))


from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def safe_goto(page, url, **kwargs):
    """Try to navigate up to 3×, with an increased timeout."""
    for attempt in range(1, 4):
        try:
            return page.goto(url, timeout=60000, **kwargs)
        except PlaywrightTimeoutError:
            print(f"⚠️ Timeout loading {url!r} (attempt {attempt}/3)")
    print(f"❌ Failed to load {url!r} after 3 attempts, skipping.")
    return None


def scrape_hotels_in_region(page, region_url):
    """
    Visit a region page, skip if there are no hotels,
    otherwise loop through all paginated results and scrape each hotel.
    """
    print(f"\n→ Navigating to region {region_url}")
    nav = safe_goto(page, region_url, wait_until="networkidle")
    if not nav:
        return []

    # give the page a moment to render its hotel section
    page.wait_for_timeout(1000)

    # 1) Detect an empty region: no <article class="sr_item">
    if not page.query_selector("article.sr_item"):
        print(f"   • no hotels in {region_url}, skipping.")
        return []

    # 2) Otherwise collect all pages
    hotels = []
    page_num = 1
    while True:
        print(f"   • scraping page {page_num} of hotels…")
        items = page.query_selector_all("article.sr_item a.pdp-link")
        detail_urls = [
            BASE_URL + it.get_attribute("href")
            for it in items
            if it.get_attribute("href")
        ]

        for url in detail_urls:
            hotels.append(scrape_hotel_details(page, url))

        # try to click Next
        next_btn = page.query_selector("a.k-pager-nav[aria-label*='next']")
        if not next_btn or next_btn.get_attribute("aria-disabled") == "true":
            break

        try:
            next_btn.click()
            page.wait_for_timeout(1000)
            page_num += 1
        except Exception as e:
            print("   ⚠️ could not click Next:", e)
            break

    print(f"   ✓ found {len(hotels)} hotels in {region_url}")
    return hotels


def scrape_hotel_details(page, url):
    """
    Visit a hotel page and extract Name, Street, AddressLine2, City, Postcode.
    """
    page.goto(url, wait_until="networkidle")
    time.sleep(0.5)
    name = ""
    street = city = postcode = addr2 = ""
    try:
        h1 = page.query_selector("h1")
        name = h1.inner_text().strip() if h1 else ""
        # Try multiple container selectors
        addr_container = (
            page.query_selector(".address-container")
            or page.query_selector(".hotel-address")
            or page.query_selector(".pdp-address")
        )
        if addr_container:
            street_el = addr_container.query_selector(".street-address")
            street = street_el.inner_text().strip() if street_el else ""
            addr2_el = addr_container.query_selector(".extended-address")
            addr2 = addr2_el.inner_text().strip() if addr2_el else ""
            city_el = addr_container.query_selector(".locality")
            city = city_el.inner_text().strip() if city_el else ""
            pc_el = addr_container.query_selector(".postal-code")
            postcode = pc_el.inner_text().strip() if pc_el else ""
    except Exception:
        # leave blank if anything goes wrong
        pass

    return {
        "Name": name,
        "Street": street,
        "AddressLine2": addr2,
        "City": city,
        "Postcode": postcode,
        "URL": url,
    }


def main():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        page.route("**/*", block_route)

        # ← inject the consent cookie BEFORE any navigation
        page.context.add_cookies(
            [
                {
                    "name": "CookieConsent",
                    "value": "true",
                    "domain": "www.bestwestern.co.uk",
                    "path": "/",
                    "secure": True,
                    "httpOnly": False,
                }
            ]
        )

        # now navigate, no banner to block you
        page.set_default_navigation_timeout(0)
        page.goto(DESTINATIONS_URL, wait_until="domcontentloaded")

        page.wait_for_selector(".house-grid", timeout=30000)

        # expand the main “Show more” buttons once and for all
        expand_all_destinations(page)

        # grab region links, etc...
        region_links = get_destination_links(page)
        print(f"→ Found {len(region_links)} region URLs")

        all_hotels = []
        for region in region_links:
            print(f"\nScraping region: {region}")
            all_hotels.extend(scrape_hotels_in_region(page, region))

        # Save results
        df = pd.DataFrame(all_hotels)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"\n✅ Saved {len(df)} hotels to {OUTPUT_CSV}")

        browser.close()


if __name__ == "__main__":
    main()

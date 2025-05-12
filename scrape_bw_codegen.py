#!/usr/bin/env python3
import os
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError

BASE_URL = "https://www.bestwestern.co.uk"
DEST_URL = f"{BASE_URL}/destinations"


def expand_show_more(page):
    while True:
        btns = page.locator('a:has-text("Show more")')
        if not btns.count():
            break
        btns.first.click()
        page.wait_for_timeout(500)


def collect_region_links(page):
    anchors = page.locator('a:has-text("Hotels in")')
    links = set()
    for i in range(anchors.count()):
        href = anchors.nth(i).get_attribute("href") or ""
        if href:
            links.add(href if href.startswith("http") else BASE_URL + href)
    return sorted(links)


def scrape_region_cards(page, url):
    """
    Returns a list of dicts with Name, Street, City, Postcode, URL
    scraped directly from the listing cards in that region.
    """
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_selector("#search-results", timeout=10000)
    except TimeoutError:
        return []

    rows = []
    seen = set()

    while True:
        page.wait_for_timeout(500)
        cards = page.locator("#search-results article.sr_item")
        if cards.count() == 0:
            break

        for i in range(cards.count()):
            c = cards.nth(i)
            name = c.locator("h3 a").inner_text().strip()

            # Refined selector: pick only the non‐.sr_local_attraction span
            addr_el = c.locator(
                ".sr_item--x2__below-title > div > span:not(.sr_local_attraction)"
            ).first
            addr = addr_el.inner_text().strip() if addr_el else ""

            parts = [p.strip() for p in addr.split(",")]
            street = parts[0] if len(parts) >= 1 else ""
            city = (
                parts[1] if len(parts) >= 3 else (parts[1] if len(parts) >= 2 else "")
            )
            postcode = parts[-1] if parts else ""

            href = c.locator("a.pdp-link").first.get_attribute("href") or ""
            full_url = href if href.startswith("http") else BASE_URL + href

            key = (name, street, city, postcode)
            if key in seen:
                continue
            seen.add(key)

            rows.append(
                {
                    "Name": name,
                    "Street": street,
                    "AddressLine2": "",
                    "City": city,
                    "Postcode": postcode,
                    "URL": full_url,
                }
            )

        # Next‐page logic unchanged…
        pager = page.locator(
            "div[data-search-pager] a.k-pager-nav[aria-label*='next']:not(.k-state-disabled)"
        )
        if not pager.count():
            break

        # JS click fallback
        page.evaluate(
            """
            () => {
                const btn = document.querySelector(
                  "div[data-search-pager] a.k-pager-nav[aria-label*='next']:not(.k-state-disabled)"
                );
                btn && btn.scrollIntoView({ block: "center" });
            }
        """
        )
        page.wait_for_timeout(200)
        page.evaluate(
            """
            () => {
                const btn = document.querySelector(
                  "div[data-search-pager] a.k-pager-nav[aria-label*='next']:not(.k-state-disabled)"
                );
                btn && btn.click();
            }
        """
        )
        page.wait_for_timeout(1000)

    return rows


def main():
    # figure out exactly where we're writing
    out_csv = os.path.abspath("hotels_uk.csv")
    print("→ Output CSV will be:", out_csv)

    all_rows = []
    seen = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        # 1) load Destinations and accept cookies
        page.goto(DEST_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.get_by_role("button", name="Allow all", exact=True).click(timeout=5000)
        except TimeoutError:
            pass

        # 2) expand and collect regions
        expand_show_more(page)
        regions = collect_region_links(page)
        print(f"→ Found {len(regions)} regions")

        # 3) scrape each region
        for idx, region in enumerate(regions, 1):
            print(f"  • ({idx}/{len(regions)}) {region}")
            rows = scrape_region_cards(page, region)
            for r in rows:
                key = (r["Name"], r["Street"], r["City"], r["Postcode"])
                if key in seen:
                    continue
                seen.add(key)
                all_rows.append(r)

        browser.close()

    # 4) write once at end
    print(f"→ Writing {len(all_rows)} unique hotel rows to CSV…")
    df = pd.DataFrame(all_rows)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print("✅ Done!")

    # 5) preview
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()

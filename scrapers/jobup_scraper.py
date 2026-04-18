import logging
from typing import List
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job
from scrapers.utils import get_headers, random_sleep, async_retry

logger = logging.getLogger(__name__)

# jobup.ch region codes for Romandy cantons
CANTON_CODES = {
    "GE": "25",
    "VD": "22",
    "NE": "24",
    "FR": "10",
    "VS": "23",
}

BASE_URL = "https://www.jobup.ch/fr/emplois/"


class JobupScraper(BaseScraper):
    """Scrapes jobup.ch for French-speaking Switzerland jobs."""

    SOURCE = "jobup.ch"

    async def scrape(self) -> List[Job]:
        jobs: List[Job] = []
        search_cfg = self.config["search"]
        cantons = search_cfg.get("cantons", list(CANTON_CODES.keys()))

        for category, cat_cfg in search_cfg["categories"].items():
            for keyword in cat_cfg["keywords"][:4]:  # top 4 keywords
                for canton in cantons[:3]:  # top 3 cantons
                    region_code = CANTON_CODES.get(canton)
                    if not region_code:
                        continue
                    found = await self._scrape_page(keyword, region_code, category)
                    jobs.extend(found)
                    await random_sleep()

        logger.info("jobup: found %d jobs", len(jobs))
        return jobs

    @async_retry(max_attempts=2)
    async def _scrape_page(self, keyword: str, region_code: str, category: str) -> List[Job]:
        params = {"term": keyword, "region": region_code}
        url = BASE_URL + "?" + urlencode(params)

        async with httpx.AsyncClient(headers=get_headers(), timeout=15, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                if response.status_code == 403:
                    logger.debug("jobup.ch returned 403, trying Playwright fallback")
                    return await self._playwright_scrape(url, keyword, region_code, category)
                response.raise_for_status()
                return self._parse_html(response.text, category, url)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    return await self._playwright_scrape(url, keyword, region_code, category)
                logger.warning("jobup HTTP error for %s: %s", keyword, exc)
                return []

    def _parse_html(self, html: str, category: str, source_url: str) -> List[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # jobup.ch job card selectors (may need updating if site changes)
        selectors = [
            "article[data-cy='job-ad-preview']",
            "article.JobListItem",
            "[class*='JobListItem']",
            "article",
        ]

        cards = []
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                break

        for card in cards[:15]:
            try:
                title_el = card.select_one("h2, h3, [class*='title'], [class*='Title']")
                company_el = card.select_one("[class*='company'], [class*='Company'], [class*='employer']")
                location_el = card.select_one("[class*='location'], [class*='Location']")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else "Suisse romande"
                href = link_el["href"] if link_el else ""

                if not href.startswith("http"):
                    href = "https://www.jobup.ch" + href

                if title and company:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        description=card.get_text(separator=" ", strip=True)[:500],
                        url=href,
                        source=self.SOURCE,
                        category=category,
                    ))
            except Exception as exc:
                logger.debug("jobup parse error: %s", exc)

        return jobs

    async def _playwright_scrape(self, url: str, keyword: str, region_code: str, category: str) -> List[Job]:
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError:
            logger.warning("Playwright not installed — skipping jobup.ch fallback. Run: playwright install chromium")
            return []

        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                extra_http_headers={"Accept-Language": "fr-CH,fr;q=0.9"}
            )
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(2000)
                html = await page.content()
                jobs = self._parse_html(html, category, url)
            except Exception as exc:
                logger.warning("Playwright jobup error for %s: %s", keyword, exc)
            finally:
                await browser.close()

        return jobs

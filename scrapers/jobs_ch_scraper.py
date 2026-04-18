import logging
from typing import List
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job
from scrapers.utils import get_headers, random_sleep, async_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://www.jobs.ch/fr/vacances-emploi/"


class JobsChScraper(BaseScraper):
    """Scrapes jobs.ch for French-speaking Switzerland jobs."""

    SOURCE = "jobs.ch"

    async def scrape(self) -> List[Job]:
        jobs: List[Job] = []
        search_cfg = self.config["search"]

        for category, cat_cfg in search_cfg["categories"].items():
            for keyword in cat_cfg["keywords"][:4]:
                for location in search_cfg["locations"][:3]:
                    found = await self._scrape_page(keyword, location, category)
                    jobs.extend(found)
                    await random_sleep()

        logger.info("jobs.ch: found %d jobs", len(jobs))
        return jobs

    @async_retry(max_attempts=2)
    async def _scrape_page(self, keyword: str, location: str, category: str) -> List[Job]:
        params = {"term": keyword, "location": location}
        url = BASE_URL + "?" + urlencode(params)

        async with httpx.AsyncClient(headers=get_headers(), timeout=15, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                if response.status_code == 403:
                    return await self._playwright_scrape(url, keyword, location, category)
                response.raise_for_status()
                return self._parse_html(response.text, category, location)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 403:
                    return await self._playwright_scrape(url, keyword, location, category)
                logger.warning("jobs.ch HTTP error for %s/%s: %s", keyword, location, exc)
                return []

    def _parse_html(self, html: str, category: str, location: str) -> List[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        selectors = [
            "[data-cy='job-ad-preview']",
            "article[class*='job']",
            "div[class*='JobItem']",
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
                company_el = card.select_one("[class*='company'], [class*='Company']")
                location_el = card.select_one("[class*='location'], [class*='Location']")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else location
                href = link_el["href"] if link_el else ""

                if not href.startswith("http"):
                    href = "https://www.jobs.ch" + href

                if title and company:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=loc,
                        description=card.get_text(separator=" ", strip=True)[:500],
                        url=href,
                        source=self.SOURCE,
                        category=category,
                    ))
            except Exception as exc:
                logger.debug("jobs.ch parse error: %s", exc)

        return jobs

    async def _playwright_scrape(self, url: str, keyword: str, location: str, category: str) -> List[Job]:
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError:
            logger.warning("Playwright not installed — skipping jobs.ch fallback")
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
                jobs = self._parse_html(html, category, location)
            except Exception as exc:
                logger.warning("Playwright jobs.ch error for %s/%s: %s", keyword, location, exc)
            finally:
                await browser.close()

        return jobs

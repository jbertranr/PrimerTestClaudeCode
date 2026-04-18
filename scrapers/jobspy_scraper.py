import logging
from typing import List

from scrapers.base import BaseScraper, Job
from scrapers.utils import async_retry

logger = logging.getLogger(__name__)


class JobSpyScraper(BaseScraper):
    """Scrapes LinkedIn and Indeed Switzerland using python-jobspy."""

    SOURCE = "jobspy"

    @async_retry(max_attempts=2)
    async def scrape(self) -> List[Job]:
        try:
            from jobspy import scrape_jobs  # type: ignore
        except ImportError:
            logger.error("python-jobspy not installed. Run: pip install python-jobspy")
            return []

        jobs: List[Job] = []
        search_cfg = self.config["search"]
        hours_old = search_cfg.get("hours_old", 24)

        for category, cat_cfg in search_cfg["categories"].items():
            keywords = cat_cfg["keywords"]
            max_results = cat_cfg.get("max_results_per_source", 15)

            # Cluster keywords into groups of 2 to reduce API calls
            keyword_groups = [
                " OR ".join(keywords[i:i+2])
                for i in range(0, len(keywords), 2)
            ]

            for location in search_cfg["locations"][:3]:  # top 3 cities per run
                for keyword_group in keyword_groups[:3]:  # top 3 keyword groups
                    try:
                        df = scrape_jobs(
                            site_name=["linkedin", "indeed"],
                            search_term=keyword_group,
                            location=f"{location}, Suisse",
                            results_wanted=max_results,
                            hours_old=hours_old,
                            country_indeed="Switzerland",
                        )

                        for _, row in df.iterrows():
                            url = str(row.get("job_url", "") or "")
                            if not url:
                                continue

                            job = Job(
                                title=str(row.get("title", "") or "").strip(),
                                company=str(row.get("company", "") or "").strip(),
                                location=str(row.get("location", location) or location).strip(),
                                description=str(row.get("description", "") or "")[:2000],
                                url=url,
                                source=str(row.get("site", self.SOURCE)),
                                category=category,
                                posted_at=str(row.get("date_posted", "unknown") or "unknown"),
                                salary=str(row.get("min_amount", "") or ""),
                            )
                            if job.title and job.company:
                                jobs.append(job)

                    except Exception as exc:
                        logger.warning(
                            "jobspy error for '%s' in %s: %s", keyword_group, location, exc
                        )

        logger.info("jobspy: found %d jobs", len(jobs))
        return jobs

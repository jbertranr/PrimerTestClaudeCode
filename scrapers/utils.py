import asyncio
import random
import logging
from functools import wraps

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-CH,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def get_headers() -> dict:
    return {**BASE_HEADERS, "User-Agent": random.choice(USER_AGENTS)}


async def random_sleep(min_s: float = 0.8, max_s: float = 2.5) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


def async_retry(max_attempts: int = 3, delay: float = 2.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc
                        )
                        return []
                    wait = delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s attempt %d/%d failed (%s) — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, wait
                    )
                    await asyncio.sleep(wait)
        return wrapper
    return decorator

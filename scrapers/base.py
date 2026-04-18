import hashlib
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import List


@dataclass
class Job:
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    category: str
    posted_at: str = "unknown"
    salary: str = ""
    cover_letter: str = ""
    subject_line: str = ""
    id: str = field(init=False)

    def __post_init__(self):
        raw = f"{self.title}|{self.company}|{self.url}"
        self.id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def __repr__(self):
        return f"<Job [{self.source}] {self.title} @ {self.company} — {self.location}>"


class BaseScraper(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def scrape(self) -> List[Job]:
        """Return a list of Job objects found in this run."""
        ...

"""
Post-scraping filters: geography (Switzerland only) and keyword relevance.
"""

from scrapers.base import Job
from typing import List

# Swiss cities and cantons — only these are accepted
SWISS_LOCATIONS = {
    "genève", "geneva", "ge",
    "lausanne", "vaud", "vd",
    "neuchâtel", "neuchatel", "ne",
    "fribourg", "fr",
    "sion", "valais", "vs",
    "martigny", "montreux", "verbier", "crans-montana", "zermatt",
    "nyon", "morges", "yverdon", "vevey", "aigle", "sierre",
    "suisse", "switzerland", "schweiz", "svizzera",
}

# French cities/regions to explicitly exclude
FRANCE_LOCATIONS = {
    "paris", "france", "lyon", "marseille", "toulouse", "bordeaux",
    "nice", "nantes", "strasbourg", "montpellier", "lille", "rennes",
    "annecy", "grenoble", "chambéry", "chambery", "savoie", "haute-savoie",
    "rhône", "rhone", "alsace", "bretagne", "normandie",
    "ile-de-france", "île-de-france", "provence",
}

# Hospitality keywords — at least one must appear in title or description
HOSPITALITY_TERMS = {
    "serveur", "serveuse", "restauration", "hôtellerie", "hotelerie",
    "hotel", "hôtel", "barman", "barmaid", "chef de rang", "f&b", "f & b",
    "waiter", "waitress", "gastro", "gastronomie", "cuisine", "cuisinier",
    "cuistot", "room service", "banquet", "traiteur", "brasserie", "bistro",
    "réceptionniste", "reception", "réception", "front desk", "concierge",
}

# Tourism keywords
TOURISM_TERMS = {
    "tourisme", "tourism", "touristique", "voyage", "voyages",
    "guide touristique", "office du tourisme", "agent de voyages",
    "animateur", "excursion", "réservation", "reservation",
    "billetterie", "tour operator", "destination",
}

CATEGORY_TERMS = {
    "hospitality": HOSPITALITY_TERMS,
    "tourism": TOURISM_TERMS,
}


def _normalize(text: str) -> str:
    return text.lower().strip()


def _is_swiss(job: Job) -> bool:
    """Return True if the job location is in Switzerland."""
    loc = _normalize(job.location)

    # Explicit France → reject
    if any(fr in loc for fr in FRANCE_LOCATIONS):
        return False

    # Must contain at least one Swiss place name
    if any(ch in loc for ch in SWISS_LOCATIONS):
        return True

    # If location is ambiguous (e.g. empty or just "Remote"), allow it
    # only if the description also contains Swiss references
    desc = _normalize(job.description)
    if any(ch in desc for ch in SWISS_LOCATIONS):
        return True

    return False


def _is_relevant(job: Job) -> bool:
    """Return True if title or description contains a relevant keyword."""
    terms = CATEGORY_TERMS.get(job.category, set())
    title = _normalize(job.title)
    desc = _normalize(job.description)

    return any(term in title or term in desc for term in terms)


def apply_filters(jobs: List[Job]) -> List[Job]:
    """Filter jobs: Swiss locations only + relevant keywords only."""
    filtered = []
    for job in jobs:
        if not _is_swiss(job):
            continue
        if not _is_relevant(job):
            continue
        filtered.append(job)
    return filtered

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import storage.database as db_module
from scrapers.base import Job


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()


def make_job(**kwargs) -> Job:
    defaults = dict(
        title="Serveur", company="Hotel Test", location="Genève",
        description="", url="https://example.com/job/1",
        source="test", category="hospitality"
    )
    defaults.update(kwargs)
    return Job(**defaults)


def test_new_job_is_new():
    job = make_job()
    assert db_module.is_new(job.id)


def test_seen_job_not_new():
    job = make_job()
    db_module.mark_seen(job)
    assert not db_module.is_new(job.id)


def test_different_jobs_have_different_ids():
    j1 = make_job(url="https://example.com/1")
    j2 = make_job(url="https://example.com/2")
    assert j1.id != j2.id


def test_mark_cover_letter_done():
    job = make_job()
    db_module.mark_seen(job)
    db_module.mark_cover_letter_done(job.id)
    # Should not raise; just verify it runs without error

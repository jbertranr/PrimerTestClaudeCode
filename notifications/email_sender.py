import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from scrapers.base import Job

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "hospitality": "Hôtellerie / Restauration",
    "tourism": "Tourisme",
}


def _build_html(jobs: List[Job]) -> str:
    today = datetime.now().strftime("%d %B %Y")
    rows = ""
    for job in jobs:
        cat = CATEGORY_LABELS.get(job.category, job.category)
        letter_html = (
            f"<details><summary>📝 Lettre de motivation</summary>"
            f"<pre>{job.cover_letter}</pre></details>"
            if job.cover_letter
            else ""
        )
        rows += f"""
        <tr>
          <td><a href="{job.url}"><strong>{job.title}</strong></a></td>
          <td>{job.company}</td>
          <td>{job.location}</td>
          <td>{cat}</td>
          <td>{job.posted_at}</td>
          <td>{job.source}</td>
        </tr>
        {"<tr><td colspan='6'>" + letter_html + "</td></tr>" if letter_html else ""}
        """

    return f"""
    <html><body>
    <h2>Rapport quotidien — {today}</h2>
    <p>{len(jobs)} nouveaux postes trouvés en Suisse romande.</p>
    <table border="1" cellpadding="6" cellspacing="0">
      <thead>
        <tr>
          <th>Poste</th><th>Entreprise</th><th>Lieu</th>
          <th>Catégorie</th><th>Publié</th><th>Source</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    </body></html>
    """


def send_digest(jobs: List[Job]) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    to_addr = os.environ.get("SMTP_TO", user)

    if not user or not password:
        logger.error("Email credentials missing — set SMTP_USER and SMTP_PASSWORD in .env")
        return

    today = datetime.now().strftime("%d/%m/%Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Swiss Jobs] {len(jobs)} nouveaux postes — {today}"
    msg["From"] = user
    msg["To"] = to_addr

    msg.attach(MIMEText(_build_html(jobs), "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(user, to_addr, msg.as_string())
        logger.info("Email digest sent to %s (%d jobs)", to_addr, len(jobs))
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)

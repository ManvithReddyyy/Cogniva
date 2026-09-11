import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database.repository import Repository
from app.services.email import send_email

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def send_name_request_emails():
    """
    One-shot script: send a short email to every active subscriber who
    has not yet set a display name, asking them to personalize their digest.
    """
    site_url = os.getenv("SITE_URL", "https://cogniva-hn3p.onrender.com").rstrip("/")
    if not site_url:
        logger.warning("SITE_URL env var not set — links will be relative.")

    repo = Repository()
    emails = repo.get_subscribers_without_name()

    if not emails:
        logger.info("All subscribers already have a display name set. Nothing to do.")
        return

    logger.info(f"Sending name-request emails to {len(emails)} subscriber(s)...")

    success, failed = 0, 0
    for email in emails:
        link = f"{site_url}/set-name?email={email}" if site_url else f"/set-name?email={email}"

        subject = "Personalize your Cogniva digest"
        body_text = (
            f"Hey there,\n\n"
            f"You're subscribed to the Cogniva AI news digest. We noticed you haven't set a "
            f"display name yet, so all your emails say 'Hey there'.\n\n"
            f"Set your name in 5 seconds here:\n{link}\n\n"
            f"— Cogniva"
        )
        body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 500px; margin: 0 auto; padding: 24px; }}
    a {{ color: #0066cc; text-decoration: none; font-weight: 500; }}
    a:hover {{ text-decoration: underline; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #999; }}
  </style>
</head>
<body>
  <p>Hey there,</p>
  <p>You're subscribed to the <strong>Cogniva</strong> AI news digest. We noticed you haven't set a display name yet, so all your emails just say <em>"Hey there"</em>.</p>
  <p><a href="{link}">Click here to set your name</a> — takes 5 seconds.</p>
  <p>Your next digest will greet you by name.</p>
  <p class="footer">— Cogniva</p>
</body>
</html>"""

        try:
            send_email(subject=subject, body_text=body_text, body_html=body_html, recipients=[email])
            logger.info(f"  ✓ Sent to {email}")
            success += 1
        except Exception as e:
            logger.error(f"  ✗ Failed for {email}: {e}")
            failed += 1

    logger.info(f"Done: {success} sent, {failed} failed out of {len(emails)} total.")


if __name__ == "__main__":
    send_name_request_emails()

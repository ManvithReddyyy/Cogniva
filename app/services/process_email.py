import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from app.agent.email_agent import EmailAgent, RankedArticleDetail, EmailDigestResponse
from app.agent.curator_agent import CuratorAgent
from app.profiles.user_profile import USER_PROFILE
from app.database.repository import Repository
from app.services.email import send_email, digest_to_html

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_email_digest(hours: int = 24, top_n: int = 10, only_unsent: bool = True, recipient_name: Optional[str] = None) -> Optional[EmailDigestResponse]:
    curator = CuratorAgent(USER_PROFILE)
    email_agent = EmailAgent(USER_PROFILE)
    repo = Repository()
    
    digests = repo.get_recent_digests(hours=hours, only_unsent=only_unsent)
    total = len(digests)
    
    if total == 0 and only_unsent:
        logger.info("No unsent digests found, falling back to all recent digests...")
        digests = repo.get_recent_digests(hours=hours, only_unsent=False)
        total = len(digests)
    
    if total == 0:
        logger.info(f"No recent digests found from the last {hours} hours")
        return None
    
    logger.info(f"Ranking {total} digests for email generation")
    ranked_articles = curator.rank_digests(digests)
    
    if not ranked_articles:
        logger.error("Failed to rank digests")
        raise ValueError("Failed to rank articles")
    
    logger.info(f"Generating email digest with top {top_n} articles")
    
    article_details = [
        RankedArticleDetail(
            digest_id=a.digest_id,
            rank=a.rank,
            relevance_score=a.relevance_score,
            reasoning=a.reasoning,
            title=next((d["title"] for d in digests if d["id"] == a.digest_id), ""),
            summary=next((d["summary"] for d in digests if d["id"] == a.digest_id), ""),
            url=next((d["url"] for d in digests if d["id"] == a.digest_id), ""),
            article_type=next((d["article_type"] for d in digests if d["id"] == a.digest_id), "")
        )
        for a in ranked_articles
    ]
    
    email_digest = email_agent.create_email_digest_response(
        ranked_articles=article_details,
        total_ranked=len(ranked_articles),
        limit=top_n,
        recipient_name=recipient_name
    )
    
    logger.info("Email digest generated successfully")
    return email_digest


def send_digest_email(hours: int = 24, top_n: int = 10, only_unsent: bool = True, recipients: Optional[list] = None) -> dict:
    try:
        repo = Repository()

        if recipients is None:
            # Send a personalized email to each active subscriber individually
            subscribers = repo.get_active_subscribers_with_names()
            if not subscribers:
                return {"success": True, "articles_count": 0, "notice": "No active subscribers."}

            total_sent = 0
            digest_ids_to_mark: list = []
            first = True

            for sub in subscribers:
                email_addr = sub["email"]
                name = sub["display_name"] or "there"
                try:
                    result = generate_email_digest(hours=hours, top_n=top_n, only_unsent=only_unsent, recipient_name=name)
                    if result is None:
                        continue

                    markdown_content = result.to_markdown()
                    html_content = digest_to_html(result)
                    subject = f"Daily AI News Digest — {result.introduction.greeting.split('for ')[-1] if 'for ' in result.introduction.greeting else 'Update'}"

                    send_email(subject=subject, body_text=markdown_content, body_html=html_content, recipients=[email_addr])
                    total_sent += 1

                    # Collect digest IDs from first send (same set for all)
                    if first:
                        digest_ids_to_mark = [a.digest_id for a in result.articles]
                        first = False
                except Exception as sub_err:
                    logger.error(f"Failed to send to {email_addr}: {sub_err}")

            # Mark digests as sent once after all individual sends
            if digest_ids_to_mark:
                repo.mark_digests_as_sent(digest_ids_to_mark)

            logger.info(f"Personalized digest sent to {total_sent}/{len(subscribers)} subscribers")
            return {"success": True, "articles_count": top_n, "sent_to": total_sent}

        else:
            # Specific recipient list (e.g. new subscriber welcome email)
            # Look up each recipient's display name from DB
            name_map = {s["email"]: s["display_name"] for s in repo.get_active_subscribers_with_names()}
            total_sent = 0
            for email_addr in recipients:
                name = name_map.get(email_addr.strip().lower()) or "there"
                try:
                    result = generate_email_digest(hours=hours, top_n=top_n, only_unsent=only_unsent, recipient_name=name)
                    if result is None:
                        continue
                    markdown_content = result.to_markdown()
                    html_content = digest_to_html(result)
                    subject = f"Daily AI News Digest — {result.introduction.greeting.split('for ')[-1] if 'for ' in result.introduction.greeting else 'Update'}"
                    send_email(subject=subject, body_text=markdown_content, body_html=html_content, recipients=[email_addr])
                    total_sent += 1
                except Exception as sub_err:
                    logger.error(f"Failed to send welcome digest to {email_addr}: {sub_err}")

            return {"success": True, "articles_count": top_n, "sent_to": total_sent}

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    result = send_digest_email(hours=24, top_n=10)
    if result["success"]:
        print("\n=== Email Digest Sent ===")
        print(f"Subject: {result['subject']}")
        print(f"Articles: {result['articles_count']}")
    else:
        print(f"Error: {result['error']}")


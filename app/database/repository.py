from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .models import YouTubeVideo, OpenAIArticle, AnthropicArticle, Digest, Subscriber
from .connection import get_session


class Repository:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()
    
    def create_youtube_video(self, video_id: str, title: str, url: str, channel_id: str, 
                            published_at: datetime, description: str = "", transcript: Optional[str] = None) -> Optional[YouTubeVideo]:
        existing = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if existing:
            return None
        video = YouTubeVideo(
            video_id=video_id,
            title=title,
            url=url,
            channel_id=channel_id,
            published_at=published_at,
            description=description,
            transcript=transcript
        )
        self.session.add(video)
        self.session.commit()
        return video
    
    def create_openai_article(self, guid: str, title: str, url: str, published_at: datetime,
                              description: str = "", category: Optional[str] = None) -> Optional[OpenAIArticle]:
        existing = self.session.query(OpenAIArticle).filter_by(guid=guid).first()
        if existing:
            return None
        article = OpenAIArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            category=category
        )
        self.session.add(article)
        self.session.commit()
        return article
    
    def create_anthropic_article(self, guid: str, title: str, url: str, published_at: datetime,
                                description: str = "", category: Optional[str] = None) -> Optional[AnthropicArticle]:
        existing = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if existing:
            return None
        article = AnthropicArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            category=category
        )
        self.session.add(article)
        self.session.commit()
        return article
    
    def bulk_create_youtube_videos(self, videos: List[dict]) -> int:
        new_videos = []
        for v in videos:
            existing = self.session.query(YouTubeVideo).filter_by(video_id=v["video_id"]).first()
            if not existing:
                new_videos.append(YouTubeVideo(
                    video_id=v["video_id"],
                    title=v["title"],
                    url=v["url"],
                    channel_id=v.get("channel_id", ""),
                    published_at=v["published_at"],
                    description=v.get("description", ""),
                    transcript=v.get("transcript")
                ))
        if new_videos:
            self.session.add_all(new_videos)
            self.session.commit()
        return len(new_videos)
    
    def bulk_create_openai_articles(self, articles: List[dict]) -> int:
        new_articles = []
        for a in articles:
            existing = self.session.query(OpenAIArticle).filter_by(guid=a["guid"]).first()
            if not existing:
                new_articles.append(OpenAIArticle(
                    guid=a["guid"],
                    title=a["title"],
                    url=a["url"],
                    published_at=a["published_at"],
                    description=a.get("description", ""),
                    category=a.get("category")
                ))
        if new_articles:
            self.session.add_all(new_articles)
            self.session.commit()
        return len(new_articles)
    
    def bulk_create_anthropic_articles(self, articles: List[dict]) -> int:
        new_articles = []
        for a in articles:
            existing = self.session.query(AnthropicArticle).filter_by(guid=a["guid"]).first()
            if not existing:
                new_articles.append(AnthropicArticle(
                    guid=a["guid"],
                    title=a["title"],
                    url=a["url"],
                    published_at=a["published_at"],
                    description=a.get("description", ""),
                    category=a.get("category")
                ))
        if new_articles:
            self.session.add_all(new_articles)
            self.session.commit()
        return len(new_articles)
    
    def get_anthropic_articles_without_markdown(self, limit: Optional[int] = None) -> List[AnthropicArticle]:
        query = self.session.query(AnthropicArticle).filter(AnthropicArticle.markdown.is_(None))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update_anthropic_article_markdown(self, guid: str, markdown: str) -> bool:
        article = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if article:
            article.markdown = markdown
            self.session.commit()
            return True
        return False
    
    def get_youtube_videos_without_transcript(self, limit: Optional[int] = None) -> List[YouTubeVideo]:
        query = self.session.query(YouTubeVideo).filter(YouTubeVideo.transcript.is_(None))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update_youtube_video_transcript(self, video_id: str, transcript: str) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if video:
            video.transcript = transcript
            self.session.commit()
            return True
        return False
    
    def get_articles_without_digest(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        articles = []
        seen_ids = set()
        
        digests = self.session.query(Digest).all()
        for d in digests:
            seen_ids.add(f"{d.article_type}:{d.article_id}")
        
        youtube_videos = self.session.query(YouTubeVideo).filter(
            YouTubeVideo.transcript.isnot(None),
            YouTubeVideo.transcript != "__UNAVAILABLE__"
        ).all()
        for video in youtube_videos:
            key = f"youtube:{video.video_id}"
            if key not in seen_ids:
                articles.append({
                    "type": "youtube",
                    "id": video.video_id,
                    "title": video.title,
                    "url": video.url,
                    "content": video.transcript or video.description or "",
                    "published_at": video.published_at
                })
        
        openai_articles = self.session.query(OpenAIArticle).all()
        for article in openai_articles:
            key = f"openai:{article.guid}"
            if key not in seen_ids:
                articles.append({
                    "type": "openai",
                    "id": article.guid,
                    "title": article.title,
                    "url": article.url,
                    "content": article.description or "",
                    "published_at": article.published_at
                })
        
        anthropic_articles = self.session.query(AnthropicArticle).filter(
            AnthropicArticle.markdown.isnot(None)
        ).all()
        for article in anthropic_articles:
            key = f"anthropic:{article.guid}"
            if key not in seen_ids:
                articles.append({
                    "type": "anthropic",
                    "id": article.guid,
                    "title": article.title,
                    "url": article.url,
                    "content": article.markdown or article.description or "",
                    "published_at": article.published_at
                })
        
        if limit:
            articles = articles[:limit]
        
        return articles
    
    def create_digest(self, article_type: str, article_id: str, url: str, title: str, summary: str, published_at: Optional[datetime] = None) -> Optional[Digest]:
        digest_id = f"{article_type}:{article_id}"
        existing = self.session.query(Digest).filter_by(id=digest_id).first()
        if existing:
            return None
        
        if published_at:
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            created_at = published_at
        else:
            created_at = datetime.now(timezone.utc)
        
        digest = Digest(
            id=digest_id,
            article_type=article_type,
            article_id=article_id,
            url=url,
            title=title,
            summary=summary,
            created_at=created_at
        )
        self.session.add(digest)
        self.session.commit()
        return digest
    
    def get_recent_digests(self, hours: int = 24, only_unsent: bool = False) -> List[Dict[str, Any]]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = self.session.query(Digest).filter(Digest.created_at >= cutoff_time)
        if only_unsent:
            query = query.filter(Digest.sent_at.is_(None))
        digests = query.order_by(Digest.created_at.desc()).all()
        
        return [
            {
                "id": d.id,
                "article_type": d.article_type,
                "article_id": d.article_id,
                "url": d.url,
                "title": d.title,
                "summary": d.summary,
                "created_at": d.created_at
            }
            for d in digests
        ]

    def mark_digests_as_sent(self, digest_ids: List[str]) -> None:
        if not digest_ids:
            return
        now = datetime.now(timezone.utc)
        self.session.query(Digest).filter(Digest.id.in_(digest_ids)).update(
            {"sent_at": now}, synchronize_session=False
        )
        self.session.commit()

    def add_subscriber(self, email: str, display_name: Optional[str] = None) -> dict:
        """Add a new subscriber or reactivate an existing one."""
        email = email.strip().lower()
        name = display_name.strip() if display_name and display_name.strip() else None
        existing = self.session.query(Subscriber).filter_by(email=email).first()
        if existing:
            if existing.is_active:
                # Update display_name if a new one is supplied
                if name and not existing.display_name:
                    existing.display_name = name
                    self.session.commit()
                return {"status": "already_subscribed", "email": email}
            existing.is_active = True
            existing.subscribed_at = datetime.now(timezone.utc)
            if name:
                existing.display_name = name
            self.session.commit()
            return {"status": "resubscribed", "email": email}
        subscriber = Subscriber(
            email=email,
            display_name=name,
            subscribed_at=datetime.now(timezone.utc),
            is_active=True
        )
        self.session.add(subscriber)
        self.session.commit()
        return {"status": "subscribed", "email": email}

    def remove_subscriber(self, email: str) -> dict:
        """Deactivate a subscriber."""
        email = email.strip().lower()
        existing = self.session.query(Subscriber).filter_by(email=email).first()
        if not existing:
            return {"status": "not_found", "email": email}
        if not existing.is_active:
            return {"status": "already_unsubscribed", "email": email}
        existing.is_active = False
        self.session.commit()
        return {"status": "unsubscribed", "email": email}

    def get_active_subscribers(self) -> List[str]:
        """Get all active subscriber emails."""
        subscribers = self.session.query(Subscriber).filter_by(is_active=True).all()
        return [s.email for s in subscribers]

    def get_active_subscribers_with_names(self) -> List[Dict[str, Any]]:
        """Get active subscribers with their display names for personalized emails."""
        subscribers = self.session.query(Subscriber).filter_by(is_active=True).all()
        return [
            {"email": s.email, "display_name": s.display_name}
            for s in subscribers
        ]

    def update_subscriber_display_name(self, email: str, display_name: str) -> dict:
        """Set or update the display name for a subscriber."""
        email = email.strip().lower()
        name = display_name.strip() if display_name else None
        sub = self.session.query(Subscriber).filter_by(email=email).first()
        if not sub:
            return {"status": "not_found", "email": email}
        sub.display_name = name
        self.session.commit()
        return {"status": "updated", "email": email, "display_name": name}

    def get_subscribers_without_name(self) -> List[str]:
        """Get active subscriber emails that haven't set a display name yet."""
        subscribers = self.session.query(Subscriber).filter(
            Subscriber.is_active == True,
            Subscriber.display_name.is_(None)
        ).all()
        return [s.email for s in subscribers]

    def get_all_subscribers_details(self) -> List[dict]:
        """Get full subscriber details for admin dashboard."""
        subscribers = self.session.query(Subscriber).order_by(Subscriber.subscribed_at.desc()).all()
        return [
            {
                "email": s.email,
                "display_name": s.display_name,
                "subscribed_at": s.subscribed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if s.subscribed_at else "N/A",
                "is_active": s.is_active
            }
            for s in subscribers
        ]

    def toggle_subscriber_status(self, email: str) -> dict:
        """Pause or resume a subscriber."""
        email = email.strip().lower()
        sub = self.session.query(Subscriber).filter_by(email=email).first()
        if not sub:
            return {"status": "not_found", "email": email}
        sub.is_active = not sub.is_active
        self.session.commit()
        return {
            "status": "active" if sub.is_active else "paused",
            "is_active": sub.is_active,
            "email": email
        }

    def delete_subscriber(self, email: str) -> dict:
        """Permanently delete a subscriber."""
        email = email.strip().lower()
        sub = self.session.query(Subscriber).filter_by(email=email).first()
        if not sub:
            return {"status": "not_found", "email": email}
        self.session.delete(sub)
        self.session.commit()
        return {"status": "deleted", "email": email}



# Cogniva — AI News Intelligence Pipeline

Cogniva is an automated AI news aggregation, processing, and newsletter distribution engine. It continuously monitors top artificial intelligence sources, synthesizes raw articles and video transcripts into structured technical digests using LLMs, ranks stories based on relevance, and delivers curated email updates to subscribers.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Ingestion["1. Multi-Source Ingestion"]
        A1[YouTube Scraper]
        A2[OpenAI Blog RSS]
        A3[Anthropic Research & Blog]
    end

    subgraph Processing["2. Processing & Digest Engine"]
        B1[Transcript & Article Extraction]
        B2[Gemini 3.5 Flash Lite LLM]
        B3[Structured Article Digests]
    end

    subgraph Curation["3. Ranking & Curation"]
        C1[Curator Agent]
        C2[User Preference Scoring]
        C3[Ranked Technical Digest]
    end

    subgraph Database["4. Persistence Layer"]
        D1[(Supabase PostgreSQL)]
    end

    subgraph Delivery["5. FastAPI & Distribution"]
        E1[FastAPI Server]
        E2[Background Scheduler - 10 Min]
        E3[Subscriber API Endpoint]
        E4[Email Engine - Gmail SMTP / Resend]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> D1
    B3 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> E4
    D1 <--> E1
    E1 -->|Instant Delivery| E4
    E2 -->|Every 10 Mins| B1
    E3 -->|Save Subscriber| D1
```

---

## Core Components

### 1. Ingestion Layer (`app/scrapers/`)
- **YouTube Scraper**: Fetches recent video uploads from designated AI channels and extracts full spoken transcripts using `youtube_transcript_api`.
- **OpenAI Scraper**: Parses RSS/Atom news feeds via `feedparser` to extract product announcements and engineering updates.
- **Anthropic Scraper**: Scrapes Anthropic research posts using `Docling` and `BeautifulSoup4` to convert raw HTML into clean Markdown.

### 2. Processing & Digest Engine (`app/services/` & `app/agent/`)
- **Text Normalization**: Strips HTML tags, cleans transcripts, and formats content into standardized Markdown blocks.
- **LLM Digest Generation**: Sends article content to Google Gemini API (`gemini-3.5-flash-lite`) to extract:
  - Technical summary and key takeaways
  - Target audience suitability
  - Core takeaways and implementation details
  - Category tags and source metadata

### 3. Curation & Personalization (`app/agent/curator_agent.py`)
- Evaluates extracted digests against a configurable profile (`app/profiles/user_profile.py`).
- Assigns a numeric relevance score (0-10) and ranks articles based on technical depth, production applicability, and practical relevance.

### 4. Database Layer (`app/database/`)
Built with SQLAlchemy connected to a Supabase PostgreSQL instance:
- `articles`: Raw metadata, content, and source URLs.
- `digests`: Structured LLM outputs, summaries, scores, and sent status.
- `subscribers`: Active email subscriber registry.

### 5. Web Interface & Distribution (`app/api.py` & `app/services/email.py`)
- **Web Interface**: Lightweight, minimal HTML/CSS signup page with background glowing gradients.
- **Instant Welcome Email**: As soon as a user subscribes, FastAPI triggers a background task to immediately email them the latest AI news digest.
- **Continuous 10-Minute Scheduler**: A background thread runs every 10 minutes to automatically scrape, process, and send fresh digests.
- **Dual Email Delivery Engine**: Priority delivery using Gmail SMTP, with fallback to Resend API.

---

## Tech Stack

| Category | Technology | Purpose |
|---|---|---|
| **Core Language** | Python 3.12+ | Core pipeline & backend business logic |
| **Web & API Framework** | FastAPI, Uvicorn | Web server, asynchronous API endpoints, background tasks |
| **AI / LLM Engine** | Google GenAI SDK, Gemini 3.5 Flash Lite | Text summarization, structured JSON extraction, curation ranking |
| **Web Scraping & Ingestion** | BeautifulSoup4, Docling, Feedparser, Youtube Transcript API | Content scraping from YouTube, OpenAI RSS, and Anthropic research |
| **Database & ORM** | PostgreSQL (Supabase), SQLAlchemy ORM | Relational persistence for articles, transcripts, digests, and subscribers |
| **Email Dispatch Engine** | Gmail SMTP (`smtplib`), Resend API | Reliable multi-provider transactional newsletter delivery |
| **Package Management** | UV (`uv`) | Fast, reproducible Python dependency resolution |
| **Frontend UI** | HTML5, Vanilla CSS3 | Lightweight, dark/white minimal subscriber interface |
| **Deployment & Cloud** | Render Web Services, GitHub Actions | Cloud hosting and automated workflow execution |

---

## Environment Variables Configuration

Create a `.env` file in the root directory:

```env
# Database Configuration (Supabase PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/postgres

# Google Gemini LLM
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite

# Email Credentials
MY_EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password
RESEND_API_KEY=optional_resend_api_key
```

---

## Installation & Running Locally

### 1. Install Dependencies
Using `uv`:
```bash
uv sync
```

### 2. Start Web Server & Scheduler
```bash
uv run uvicorn app.api:app --host 0.0.0.0 --port 8000
```
Access the application locally at `http://localhost:8000`.

### 3. Execute Pipeline Manually
To execute a one-off scraping and email generation run:
```bash
uv run python -m app.daily_runner
```

---

## Deployment on Render

1. Create a new **Web Service** on Render and link your repository.
2. Set the **Build Command**:
   ```bash
   pip install uv && uv sync
   ```
3. Set the **Start Command**:
   ```bash
   uv run uvicorn app.api:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variables under **Environment** settings in Render dashboard.

---

## License

MIT License. Developed for automated AI intelligence distribution.

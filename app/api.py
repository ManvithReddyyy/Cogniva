import os
import re
import logging
import threading
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from app.database.models import Base
from app.database.connection import engine
from app.database.repository import Repository
from app.services.process_email import send_digest_email
from app.daily_runner import run_daily_pipeline

# Create tables on startup (including subscribers)
Base.metadata.create_all(engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Cogniva", description="AI News Intelligence Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def start_background_scheduler():
    def scheduler_loop():
        logger.info("Background 10-minute scheduler thread initialized.")
        while True:
            time.sleep(600)  # Wait 10 minutes (600s)
            try:
                logger.info("Triggering 10-minute background pipeline run...")
                run_daily_pipeline(hours=24, top_n=5)
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()


@app.on_event("startup")
def on_startup():
    start_background_scheduler()


class EmailRequest(BaseModel):
    email: str


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


@app.post("/api/subscribe")
async def subscribe(request: EmailRequest, background_tasks: BackgroundTasks):
    email = request.email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    try:
        repo = Repository()
        result = repo.add_subscriber(email)
        logger.info(f"Subscription: {result}")
        
        # Instantly send current AI news digest to new subscriber in background
        background_tasks.add_task(send_digest_email, hours=24, top_n=5, only_unsent=False, recipients=[email])

        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe. Please try again.")


@app.post("/api/unsubscribe")
async def unsubscribe(request: EmailRequest):
    email = request.email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    try:
        repo = Repository()
        result = repo.remove_subscriber(email)
        logger.info(f"Unsubscription: {result}")
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe. Please try again.")


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve static files and index.html
static_dir = Path(__file__).parent / "static"

@app.get("/")
async def serve_index():
    return FileResponse(static_dir / "index.html")

@app.get("/unsubscribe")
async def serve_unsubscribe_page():
    return FileResponse(static_dir / "index.html")


if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

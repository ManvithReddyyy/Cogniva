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


INTERVAL_SECONDS = 14400  # 4 hours

pipeline_activity = {
    "last_run_time": None,
    "last_run_duration": None,
    "last_run_status": "Idle",
    "last_run_summary": None,
    "next_run_time": (time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() + INTERVAL_SECONDS)))
}


def execute_pipeline():
    global pipeline_activity
    start = time.time()
    pipeline_activity["last_run_status"] = "Running"
    pipeline_activity["last_run_time"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    try:
        res = run_daily_pipeline(hours=24, top_n=5)
        duration = time.time() - start
        pipeline_activity["last_run_duration"] = f"{duration:.1f}s"
        pipeline_activity["last_run_status"] = "Success" if res.get("success") else "Warning"
        pipeline_activity["last_run_summary"] = {
            "scraped": res.get("scraping", {}),
            "processed": res.get("processing", {}),
            "digests": res.get("digests", {}),
            "email": res.get("email", {})
        }
    except Exception as e:
        pipeline_activity["last_run_status"] = f"Failed: {e}"
        logger.error(f"Pipeline execution error: {e}")
    finally:
        pipeline_activity["next_run_time"] = time.strftime(
            "%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() + INTERVAL_SECONDS)
        )


def start_background_scheduler():
    def scheduler_loop():
        logger.info("Background 4-hour scheduler thread initialized.")
        while True:
            time.sleep(INTERVAL_SECONDS)  # 4 hours (14400s)
            try:
                logger.info("Triggering 4-hour background pipeline run...")
                execute_pipeline()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()


@app.on_event("startup")
def on_startup():
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(engine)
        logger.info("Database tables verified.")
    except Exception as e:
        logger.error(f"Database startup notice: {e}")
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


@app.get("/api/admin/subscribers")
async def get_admin_subscribers():
    try:
        repo = Repository()
        subscribers = repo.get_all_subscribers_details()
        return {"subscribers": subscribers}
    except Exception as e:
        logger.error(f"Error fetching subscribers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/subscribers/add")
async def add_subscriber_manually(request: EmailRequest, background_tasks: BackgroundTasks):
    email = request.email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    try:
        repo = Repository()
        result = repo.add_subscriber(email)
        logger.info(f"Manual subscriber added by admin: {email}")

        # Instantly send news digest email to the new subscriber
        background_tasks.add_task(send_digest_email, hours=24, top_n=5, only_unsent=False, recipients=[email])

        return JSONResponse(content={"status": "success", "result": result, "email": email})
    except Exception as e:
        logger.error(f"Error manually adding subscriber: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/subscribers/toggle")
async def toggle_subscriber(request: EmailRequest):
    email = request.email.strip().lower()
    try:
        repo = Repository()
        result = repo.toggle_subscriber_status(email)
        logger.info(f"Subscriber status toggled: {result}")
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error toggling subscriber: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/subscribers/delete")
async def delete_subscriber(request: EmailRequest):
    email = request.email.strip().lower()
    try:
        repo = Repository()
        result = repo.delete_subscriber(email)
        logger.info(f"Subscriber deleted: {result}")
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error deleting subscriber: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve static files and index.html
static_dir = Path(__file__).parent / "static"

@app.get("/")
async def serve_index():
    return FileResponse(static_dir / "index.html")

@app.get("/admin")
async def serve_admin_page():
    return FileResponse(static_dir / "admin.html")

@app.get("/unsubscribe")
async def serve_unsubscribe_page():
    return FileResponse(static_dir / "index.html")


if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server directly on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

import json
import time
import os
from backend.app.celery_app import celery_app

JOBS_DIR = "backend/storage/jobs"

@celery_app.task
def process_video(job_id: str):
    job_file = os.path.join(JOBS_DIR, f"{job_id}.json")

    # 🔄 Load job
    with open(job_file, "r") as f:
        job = json.load(f)

    # 🔥 Update status → processing
    job["status"] = "processing"
    with open(job_file, "w") as f:
        json.dump(job, f, indent=4)

    # ⏳ simulate heavy work (replace later with Whisper)
    time.sleep(10)

    # 🔥 Update status → completed
    job["status"] = "completed"
    job["result"] = "captions generated (fake for now)"

    with open(job_file, "w") as f:
        json.dump(job, f, indent=4)
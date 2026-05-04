import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.app.tasks import process_video

router = APIRouter()

@router.get("/test")
def test_route():
    return {"message": "captions route working"}


UPLOAD_DIR = "backend/storage/uploads"
JOBS_DIR = "backend/storage/jobs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)


@router.post("/generate")
async def generate(file: UploadFile = File(...)):
    
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")

    #  1. Generate unique job ID
    job_id = str(uuid.uuid4())

    #  2. Save file with job_id
    file_ext = file.filename.split(".")[-1]
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}.{file_ext}")

    print("Current working dir:", os.getcwd())
    print("Saving file to:", file_path)
  #print("Saving job to:", job_file)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    #  3.Create job metadata
    job_data = {
        "job_id": job_id,
        "status": "uploaded",
        "file_path": file_path,
        "result": None
    }

    #  4. Save job JSON
    job_file = os.path.join(JOBS_DIR, f"{job_id}.json")
    with open(job_file, "w") as f:
        json.dump(job_data, f, indent=4)
        
    # AFTER saving job JSON
    process_video.delay(job_id)  # 🔥 send to background worker
    return {
        "message": "job created",
        "job_id": job_id
    }

@router.get("/status/{job_id}")
def get_status(job_id: str):
    job_file = os.path.join(JOBS_DIR, f"{job_id}.json")

    if not os.path.exists(job_file):
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job_file, "r") as f:
        job_data = json.load(f)

    return job_data
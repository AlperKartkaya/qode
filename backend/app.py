from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import shutil
import uuid

from config import settings
from ogw_client import OGWClient
from docker_runner import run_inference_container

app = FastAPI(title="QoDe Backend API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ogw = OGWClient()

# Global state to keep track of inference status and progress
inference_status = "IDLE"  # IDLE, UPLOADED, PROCESSING, DONE, FAILED
inference_progress = 0.0
inference_message = ""

class TokenRequest(BaseModel):
    code: str

class VerifyRequest(BaseModel):
    access_token: str
    phone_number: str

class QoDRequest(BaseModel):
    access_token: str
    duration: int = 60

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/token")
async def exchange_token(req: TokenRequest):
    result = await ogw.get_access_token(req.code)
    if not result:
        raise HTTPException(status_code=400, detail="Could not exchange token")
    return result

@app.post("/nv/verify")
async def verify_number(req: VerifyRequest):
    if settings.allow_mock_gateway and req.access_token == "mock-token":
        return {"devicePhoneNumberVerified": True}
    verified = await ogw.verify_number(req.access_token, req.phone_number)
    return {"devicePhoneNumberVerified": verified}

@app.post("/qod/session")
async def create_qod_session(req: QoDRequest):
    if settings.allow_mock_gateway and req.access_token == "mock-token":
        return {"sessionId": str(uuid.uuid4()), "duration": req.duration}
    session = await ogw.create_qod_session(req.access_token, req.duration)
    if not session:
        raise HTTPException(status_code=400, detail="Could not create QoD session")
    return session

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    global inference_status, inference_progress, inference_message
    os.makedirs(settings.data_input_dir, exist_ok=True)
    
    file_path = os.path.join(settings.data_input_dir, "video.mp4")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # A new upload must never inherit a successful result from a previous run.
    stale_result = os.path.join(settings.data_output_dir, "results.json")
    if os.path.exists(stale_result):
        os.remove(stale_result)
        
    inference_status = "UPLOADED"
    inference_progress = 0.05
    inference_message = "Video uploaded to backend"
    return {"message": "Video uploaded successfully", "filename": "video.mp4"}

def background_inference():
    global inference_status, inference_progress, inference_message
    inference_status = "PROCESSING"
    inference_progress = 0.15
    inference_message = "Initializing AI Container & Models (YOLO11x)..."
    
    container = run_inference_container()
    if container:
        result = container.wait()
        if result['StatusCode'] == 0:
            result_path = os.path.join(settings.data_output_dir, "results.json")
            if os.path.isfile(result_path):
                inference_status = "DONE"
                inference_progress = 1.0
                inference_message = "Inference Complete!"
            else:
                inference_status = "FAILED"
                inference_progress = 0.0
                inference_message = "Inference exited without results.json"
        else:
            inference_status = "FAILED"
            inference_progress = 0.0
            inference_message = "Inference Error"
    else:
        inference_status = "FAILED"
        inference_progress = 0.0
        inference_message = "Docker daemon is unavailable; inference was not run"

@app.post("/ai-run")
async def run_ai(background_tasks: BackgroundTasks):
    global inference_status
    if inference_status == "PROCESSING":
        return {"status": "Already processing"}
        
    background_tasks.add_task(background_inference)
    return {"status": "Inference started"}

@app.get("/ai-result")
def get_ai_result():
    global inference_status, inference_progress, inference_message
    
    result_path = os.path.join(settings.data_output_dir, "results.json")
    if inference_status == "DONE" and os.path.exists(result_path):
        with open(result_path, "r") as f:
            data = json.load(f)
        return {
            "status": "DONE",
            "progress": 1.0,
            "message": "Analysis Complete!",
            "result": data
        }
            
    return {
        "status": inference_status,
        "progress": inference_progress,
        "message": inference_message
    }

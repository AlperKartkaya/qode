from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import shutil

from .config import settings
from .ogw_client import OGWClient
from .docker_runner import run_inference_container

app = FastAPI(title="QoDe Backend API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ogw = OGWClient()

# Global state to keep track of inference status
inference_status = "IDLE"  # IDLE, UPLOADED, PROCESSING, DONE, FAILED

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
    verified = await ogw.verify_number(req.access_token, req.phone_number)
    return {"devicePhoneNumberVerified": verified}

@app.post("/qod/session")
async def create_qod_session(req: QoDRequest):
    session = await ogw.create_qod_session(req.access_token, req.duration)
    if not session:
        raise HTTPException(status_code=400, detail="Could not create QoD session")
    return session

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    global inference_status
    os.makedirs(settings.data_input_dir, exist_ok=True)
    
    file_path = os.path.join(settings.data_input_dir, "video.mp4")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    inference_status = "UPLOADED"
    return {"message": "Video uploaded successfully", "filename": "video.mp4"}

def background_inference():
    global inference_status
    inference_status = "PROCESSING"
    container = run_inference_container()
    if container:
        result = container.wait()
        if result['StatusCode'] == 0:
            inference_status = "DONE"
        else:
            inference_status = "FAILED"
    else:
        # Fallback for local testing without Docker
        inference_status = "FAILED"
        print("Fallback: Container could not be started.")

@app.post("/ai-run")
async def run_ai(background_tasks: BackgroundTasks):
    global inference_status
    if inference_status == "PROCESSING":
        return {"status": "Already processing"}
        
    background_tasks.add_task(background_inference)
    return {"status": "Inference started"}

@app.get("/ai-result")
def get_ai_result():
    global inference_status
    
    if inference_status == "DONE":
        result_path = os.path.join(settings.data_output_dir, "results.json")
        if os.path.exists(result_path):
            with open(result_path, "r") as f:
                data = json.load(f)
            return {"status": "DONE", "result": data}
        else:
            return {"status": "FAILED", "detail": "results.json not found"}
            
    return {"status": inference_status}

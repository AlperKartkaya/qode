import pytest
from fastapi.testclient import TestClient
from app import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

@patch("app.ogw.verify_number")
def test_verify_endpoint_success(mock_verify):
    mock_verify.return_value = True
    response = client.post("/nv/verify", json={"access_token": "token", "phone_number": "+905390000020"})
    assert response.status_code == 200
    assert response.json()["devicePhoneNumberVerified"] is True

@patch("app.ogw.create_qod_session")
def test_qod_session_success(mock_create_qod):
    mock_create_qod.return_value = {"sessionId": "test_id", "status": "ACTIVE"}
    response = client.post("/qod/session", json={"access_token": "token", "duration": 60})
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

@patch("app.ogw.create_qod_session")
def test_qod_session_failure(mock_create_qod):
    mock_create_qod.return_value = None
    response = client.post("/qod/session", json={"access_token": "token", "duration": 60})
    assert response.status_code == 400

def test_upload_video():
    # Simulate a file upload
    file_content = b"fake video content"
    files = {"file": ("test.mp4", file_content, "video/mp4")}
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    assert response.json()["message"] == "Video uploaded successfully"

@patch("app.background_inference")
def test_ai_run(mock_bg_inference):
    response = client.post("/ai-run")
    assert response.status_code == 200
    assert response.json()["status"] == "Inference started"
    mock_bg_inference.assert_called_once()

def test_ai_result():
    response = client.get("/ai-result")
    assert response.status_code == 200
    assert "status" in response.json()

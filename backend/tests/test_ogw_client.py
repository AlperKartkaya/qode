import pytest
import asyncio
from unittest.mock import patch, MagicMock
from ogw_client import OGWClient
import os

@pytest.fixture
def ogw_client():
    # Set mock credentials
    os.environ["OGW_CLIENT_ID"] = "test_client_id"
    os.environ["OGW_CLIENT_SECRET"] = "test_client_secret"
    client = OGWClient()
    yield client
    # Clean up
    if "OGW_CLIENT_ID" in os.environ:
        del os.environ["OGW_CLIENT_ID"]
    if "OGW_CLIENT_SECRET" in os.environ:
        del os.environ["OGW_CLIENT_SECRET"]

@patch("httpx.AsyncClient.post")
def test_get_access_token_success(mock_post, ogw_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "mock_token", "expires_in": 3600}
    mock_post.return_value = mock_response

    token_data = asyncio.run(ogw_client.get_access_token(auth_code="auth123"))
    
    assert token_data["access_token"] == "mock_token"
    mock_post.assert_called_once()

@patch("httpx.AsyncClient.post")
def test_get_access_token_failure(mock_post, ogw_client):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_post.return_value = mock_response

    token_data = asyncio.run(ogw_client.get_access_token(auth_code="invalid"))
    
    assert token_data is None

@patch("httpx.AsyncClient.post")
def test_verify_number_success(mock_post, ogw_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"devicePhoneNumberVerified": True}
    mock_post.return_value = mock_response

    result = asyncio.run(
        ogw_client.verify_number(access_token="mock_token", phone_number="+905390000020")
    )
    
    assert result is True

@patch("httpx.AsyncClient.post")
def test_create_qod_session_success(mock_post, ogw_client):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"sessionId": "mock_session_id", "status": "ACTIVE"}
    mock_post.return_value = mock_response

    session = asyncio.run(ogw_client.create_qod_session(access_token="mock_token", duration=60))
    
    assert session is not None
    assert session["sessionId"] == "mock_session_id"
    assert session["status"] == "ACTIVE"

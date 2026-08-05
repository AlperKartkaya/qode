import pytest
from unittest.mock import patch, MagicMock
import docker
from docker_runner import run_inference_container

@patch("docker_runner.settings.use_gpu", False)
@patch("docker_runner.client")
def test_run_inference_container_success(mock_client):
    # Setup mock container
    mock_container = MagicMock()
    mock_client.containers.run.return_value = mock_container
    
    container = run_inference_container()
    
    assert container == mock_container
    mock_client.containers.run.assert_called_once()
    
    # Check that device_requests is empty when GPU is False
    call_args = mock_client.containers.run.call_args[1]
    assert "device_requests" in call_args
    assert call_args["device_requests"] == []

@patch("docker_runner.settings.use_gpu", True)
@patch("docker_runner.client")
def test_run_inference_container_with_gpu(mock_client):
    mock_container = MagicMock()
    mock_client.containers.run.return_value = mock_container
    
    container = run_inference_container()
    
    assert container == mock_container
    
    # Check that device_requests includes GPU request
    call_args = mock_client.containers.run.call_args[1]
    assert "device_requests" in call_args
    assert len(call_args["device_requests"]) == 1
    assert call_args["device_requests"][0].capabilities == [['gpu']]

@patch("docker_runner.client")
def test_run_inference_container_docker_error(mock_client):
    # Simulate Docker error
    mock_client.containers.run.side_effect = Exception("Docker not running")
    
    container = run_inference_container()
    
    assert container is None

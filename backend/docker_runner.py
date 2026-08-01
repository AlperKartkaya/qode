import docker
import os
from .config import settings

try:
    client = docker.from_env()
except docker.errors.DockerException:
    client = None

def run_inference_container():
    if not client:
        print("Docker daemon is not running or accessible.")
        return None
        
    input_dir = os.path.abspath(settings.data_input_dir)
    output_dir = os.path.abspath(settings.data_output_dir)
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Running docker container {settings.docker_image_name}")
    try:
        container = client.containers.run(
            settings.docker_image_name,
            detach=True,
            device_requests=[docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])],
            volumes={
                input_dir: {'bind': '/app/data/input', 'mode': 'ro'},
                output_dir: {'bind': '/app/data/output', 'mode': 'rw'}
            }
        )
        return container
    except Exception as e:
        print(f"Docker Error: {e}")
        return None

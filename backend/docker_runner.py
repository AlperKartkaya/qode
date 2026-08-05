import docker
from config import settings
import os

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
        # Settings owns environment parsing so invalid boolean values fail during
        # startup instead of silently changing the container contract here.
        use_gpu = settings.use_gpu
        device_requests = [docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])] if use_gpu else []
        
        print(f"Starting container with GPU: {use_gpu}")
        container = client.containers.run(
            settings.docker_image_name,
            detach=True,
            device_requests=device_requests,
            volumes={
                input_dir: {'bind': '/app/data/input', 'mode': 'ro'},
                output_dir: {'bind': '/app/data/output', 'mode': 'rw'}
            }
        )
        return container
    except Exception as e:
        print(f"Docker Error: {e}")
        return None

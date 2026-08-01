import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ogw_api_gateway_url: str = "https://opengateway.turkcell.com.tr"
    ogw_client_id: str = ""
    ogw_client_secret: str = ""
    backend_callback_url: str = "http://localhost:8000/api/auth/callback"
    
    docker_image_name: str = "teknofest-2026/qode:latest"
    data_input_dir: str = os.path.join(os.getcwd(), "../data/input")
    data_output_dir: str = os.path.join(os.getcwd(), "../data/output")

    class Config:
        env_file = ".env"

settings = Settings()

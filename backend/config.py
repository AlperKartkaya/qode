import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class Settings(BaseSettings):
        ogw_api_gateway_url: str = "https://opengateway.turkcell.com.tr"
        ogw_client_id: str = ""
        ogw_client_secret: str = ""
        backend_callback_url: str = "http://localhost:8000/api/auth/callback"
        
        docker_image_name: str = "teknofest-2026/qode-final:2026.08-p4"
        data_input_dir: str = os.path.join(os.getcwd(), "../data/input")
        data_output_dir: str = os.path.join(os.getcwd(), "../data/output")

        vm_name: Optional[str] = None
        vm_ip: Optional[str] = None
        vm_username: Optional[str] = None
        vm_password: Optional[str] = None
        use_gpu: Optional[str] = "False"

        model_config = SettingsConfigDict(
            env_file=".env",
            extra="ignore"
        )
except ImportError:
    from pydantic import BaseSettings
    class Settings(BaseSettings):
        ogw_api_gateway_url: str = "https://opengateway.turkcell.com.tr"
        ogw_client_id: str = ""
        ogw_client_secret: str = ""
        backend_callback_url: str = "http://localhost:8000/api/auth/callback"
        
        docker_image_name: str = "teknofest-2026/qode-final:2026.08-p4"
        data_input_dir: str = os.path.join(os.getcwd(), "../data/input")
        data_output_dir: str = os.path.join(os.getcwd(), "../data/output")

        vm_name: Optional[str] = None
        vm_ip: Optional[str] = None
        vm_username: Optional[str] = None
        vm_password: Optional[str] = None
        use_gpu: Optional[str] = "False"

        class Config:
            env_file = ".env"
            extra = "ignore"

settings = Settings()

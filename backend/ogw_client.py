import base64
import httpx
from typing import Optional, Dict, Any
from config import settings

class OGWClient:
    def __init__(self):
        self.base_url = settings.ogw_api_gateway_url
        self.client_id = settings.ogw_client_id
        self.client_secret = settings.ogw_client_secret
        self.callback_url = settings.backend_callback_url

    async def get_access_token(self, auth_code: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/oauth2/token"
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.callback_url
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[OGW Client] Token Error: {response.text}")
                return None

    async def verify_number(self, access_token: str, phone_number: str) -> bool:
        url = f"{self.base_url}/number-verification/v1/verify"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "phoneNumber": phone_number
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("devicePhoneNumberVerified", False)
            else:
                print(f"[OGW Client] NV Error: {response.text}")
                return False

    async def create_qod_session(self, access_token: str, duration: int = 60) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/quality-on-demand/v1/sessions"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "duration": duration,
            "applicationServer": {
                "ipv4Address": "0.0.0.0/0"
            },
            "qosProfile": "teknofest2026"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"[OGW Client] QoD Error: {response.text}")
                return None

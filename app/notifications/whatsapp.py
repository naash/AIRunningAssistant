import httpx

API_VERSION = "v19.0"
BASE_URL = "https://graph.facebook.com"


class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str):
        self._token = token
        self._phone_number_id = phone_number_id

    def send_message(self, to: str, message: str) -> dict:
        url = f"{BASE_URL}/{API_VERSION}/{self._phone_number_id}/messages"
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            },
        )
        response.raise_for_status()
        return response.json()

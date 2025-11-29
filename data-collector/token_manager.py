import time
import threading
import requests
import os

class TokenManager:
    def __init__(self, token_url, client_id, client_secret):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._expiry_ts = 0
        self._lock = threading.Lock()
        # secondi
        self._margin = 30


    def _request_new_token(self):
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(self.token_url, data=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"Token endpoint error: {resp.status_code} {resp.text}")
        data = resp.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 300)  # fallback se manca il campo
        if not token:
            raise RuntimeError("Token endpoint did not return access_token")
        expiry_ts = int(time.time()) + int(expires_in)
        return token, expiry_ts

    def get_token(self):
        with self._lock:
            now = int(time.time())
            # se token valido e non vicino alla scadenza, lo riuso
            if self._access_token and (self._expiry_ts - now) > self._margin:
                return self._access_token
            # altrimenti richiedo un nuovo token e aggiorno cache
            token, expiry_ts = self._request_new_token()
            self._access_token = token
            self._expiry_ts = expiry_ts
            return self._access_token

CLIENT_ID = os.getenv("CLIENT_ID", "lore25-api-client")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "FozpkBoBcLEhsFcEZNh1ySEGmsb7bYbJ")
TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

token_manager = TokenManager(TOKEN_URL, CLIENT_ID, CLIENT_SECRET)

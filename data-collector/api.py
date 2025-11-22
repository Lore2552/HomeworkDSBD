import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID", "lore25-api-client")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "FozpkBoBcLEhsFcEZNh1ySEGmsb7bYbJ")

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"


@app.route("/get_token", methods=["GET"])
def get_token():
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(TOKEN_URL, data=payload, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Failed to get token", "details": response.text}), 400

    token = response.json().get("access_token")
    return token


@app.route("/states/all", methods=["GET"])
def get_all_states():
    try:
        token = get_token()
        headers = {
            "Authorization": f"Bearer {token}"
        }
        OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
        response = requests.get(OPENSKY_STATES_URL, headers=headers)

        if response.status_code != 200:
            return jsonify({
                "error": "Failed to fetch OpenSky data",
                "details": response.text
            }), response.status_code

        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

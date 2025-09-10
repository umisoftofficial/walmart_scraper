from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from collections import OrderedDict
import requests

# -------------------------------
# 🔹 Firebase Initialization
# -------------------------------
cred = credentials.Certificate("firebase-adminsdk.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# -------------------------------
# 🔹 FastAPI App
# -------------------------------
app = FastAPI(title="Umisoft License Server")

# Request model for license validation
class LicenseRequest(BaseModel):
    license_key: str
    mac_address: str

# Example Webhook URL
WEBHOOK_URL = "https://eoogp43yq28furo.m.pipedream.net"

@app.post("/validate-license")
def validate_license(req: LicenseRequest):
    try:
        # Firestore collection
        collection_ref = db.collection("licenses")
        query = collection_ref \
            .where("license_key", "==", req.license_key) \
            .where("mac_address", "==", req.mac_address) \
            .stream()

        docs = [doc.to_dict() for doc in query]
        if not docs:
            raise HTTPException(status_code=401, detail="❌ License not found")

        license_data = docs[0]
        if not license_data.get("is_active", False):
            raise HTTPException(status_code=403, detail="❌ License inactive")

        # Send payload to webhook
        payload = OrderedDict([
            ("license_key", req.license_key),
            ("mac_address", req.mac_address),
            ("email", license_data.get("email", "")),
            ("tool_name", license_data.get("tool_name", "")),
            ("valid_until", license_data.get("valid_until", "")),
        ])
        try:
            requests.post(WEBHOOK_URL, json=payload, headers={"Content-Type":"application/json"}, timeout=10)
        except Exception as e:
            payload["webhook_error"] = str(e)

        return {"status": "✅ License valid", "data": license_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}")
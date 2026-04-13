"""
Razorpay Webhook Handler for CIWeb AI Server (Vercel)
======================================================
FILE: api/webhook.py  (place this in your ciweb-ai-server project)

HOW IT WORKS:
1. User pays Rs.11 on Razorpay
2. Razorpay calls YOUR server: POST /api/webhook
3. Your server verifies the signature (security)
4. Saves payment to Firebase
5. Creates admin_grant so user gets +50 AI messages automatically

SETUP STEPS:
1. Add this file to your Vercel project as api/webhook.py
2. Add RAZORPAY_WEBHOOK_SECRET to Vercel environment variables
3. In Razorpay Dashboard → Webhooks → Add Webhook:
   URL: https://ciweb-ai-server.vercel.app/api/webhook
   Events: payment.captured
   Secret: (create a random secret, same as env variable)
4. Deploy to Vercel
"""

import json
import hmac
import hashlib
import os
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

# Your Firebase Realtime Database URL
FIREBASE_URL = "https://testingdata-2ae22-default-rtdb.firebaseio.com"

# Razorpay Webhook Secret (set in Vercel env variables)
WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

# AI messages to grant per payment
MESSAGES_PER_PAYMENT = 50


def verify_razorpay_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay webhook signature for security."""
    if not secret:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def firebase_put(path: str, data: dict) -> bool:
    """Save data to Firebase Realtime Database."""
    url = f"{FIREBASE_URL}/{path}.json"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"Firebase error: {e}")
        return False


def firebase_post(path: str, data: dict) -> str:
    """Add data to Firebase list, returns generated key."""
    url = f"{FIREBASE_URL}/{path}.json"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    try:
        response = urllib.request.urlopen(req, timeout=5)
        result = json.loads(response.read())
        return result.get("name", "")
    except Exception as e:
        print(f"Firebase post error: {e}")
        return ""


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def do_POST(self):
        """Handle POST /api/webhook from Razorpay."""

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Verify Razorpay signature
        signature = self.headers.get("x-razorpay-signature", "")
        if not verify_razorpay_signature(body, signature, WEBHOOK_SECRET):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Invalid signature")
            print("Webhook: Invalid signature rejected")
            return

        # Parse payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        # Only handle payment.captured events
        event = payload.get("event", "")
        if event != "payment.captured":
            # Acknowledge other events but don't process
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        # Extract payment details
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        payment_id    = payment.get("id", "")
        amount        = payment.get("amount", 0)  # in paise
        amount_rupees = amount / 100
        contact       = payment.get("contact", "")
        email         = payment.get("email", "")
        status        = payment.get("status", "")
        notes         = payment.get("notes", {})

        # Get username from Razorpay notes (user should enter it)
        # Users can put their CIWeb username in the "Description" field
        username = notes.get("username", "").strip().lower()

        print(f"Payment captured: {payment_id}, Rs.{amount_rupees}, user: {username}")

        # 1. Save full payment record to Firebase
        payment_data = {
            "payment_id":    payment_id,
            "amount_rupees": amount_rupees,
            "contact":       contact,
            "email":         email,
            "status":        status,
            "username":      username,
            "ts":            int(time.time() * 1000),
            "source":        "razorpay_webhook",
            "verified":      True
        }
        firebase_post("payments", payment_data)

        # 2. Create admin_grant so frontend auto-applies +50 messages
        if username:
            grant_data = {
                "username":   username,
                "amount":     MESSAGES_PER_PAYMENT,
                "payment_id": payment_id,
                "status":     "pending",  # frontend changes to "applied"
                "ts":         int(time.time() * 1000),
                "auto":       True
            }
            firebase_post("admin_grants", grant_data)
            print(f"Admin grant created for {username}: +{MESSAGES_PER_PAYMENT} messages")
        else:
            # No username - save for manual admin review
            review_data = {
                "payment_id":    payment_id,
                "amount_rupees": amount_rupees,
                "contact":       contact,
                "email":         email,
                "status":        "needs_username",
                "ts":            int(time.time() * 1000),
                "note":          "User did not provide CIWeb username in notes"
            }
            firebase_post("payments_pending", review_data)
            print(f"Payment {payment_id} saved for manual review - no username")

        # 3. Respond 200 to Razorpay (important - must respond quickly)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success":  True,
            "payment":  payment_id,
            "messages": MESSAGES_PER_PAYMENT if username else 0
        }).encode())

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status":  "CIWeb Razorpay Webhook Active",
            "version": "1.0"
        }).encode())

    def log_message(self, format, *args):
        """Suppress default HTTP logs."""
        pass

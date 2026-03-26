import requests
import json
import os
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)

            code   = data.get('code', '')[:500]
            lesson = data.get('lesson', '')
            lang   = data.get('lang', 'en')

            if not code.strip():
                self.wfile.write(json.dumps({'feedback': ''}).encode())
                return

            API_KEY = os.environ.get('GEMINI_API_KEY', '')
            if not API_KEY:
                self.wfile.write(json.dumps({'feedback': ''}).encode())
                return

            is_hi = lang == 'hi'
            prompt = f"""Quick HTML code review for lesson "{lesson}".
{"Respond in Hinglish. Max 12 words." if is_hi else "Respond in English. Max 12 words."}
If code looks good: say something encouraging.
If there is an issue: point it out simply.
Code:
{code}"""

            url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 60, "temperature": 0.5}
            }

            response = requests.post(
                url,
                params={"key": API_KEY},
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                result   = response.json()
                feedback = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                self.wfile.write(json.dumps({'feedback': feedback}).encode())
            else:
                self.wfile.write(json.dumps({'feedback': ''}).encode())

        except Exception as e:
            self.wfile.write(json.dumps({'feedback': ''}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

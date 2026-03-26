import requests
import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        # ── CORS headers ──
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        try:
            # Read request body
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)

            message = data.get('message', '').strip()
            code    = data.get('code', '')[:500]
            lesson  = data.get('lesson', '')
            lang    = data.get('lang', 'en')
            mode    = data.get('mode', '')

            if not message:
                self.wfile.write(json.dumps({'error': 'Message required'}).encode())
                return

            # ── Get API key from Vercel environment variable ──
            import os
            API_KEY = os.environ.get('GEMINI_API_KEY', '')

            if not API_KEY:
                self.wfile.write(json.dumps({
                    'error': 'GEMINI_API_KEY not set in Vercel environment variables!'
                }).encode())
                return

            # ── Build prompt ──
            is_hi   = lang == 'hi'
            is_expl = mode == 'explain'

            if is_expl:
                prompt = message  # already built in frontend
            else:
                lang_instruction = (
                    'LANGUAGE: Hinglish (Hindi+English natural mix). Example: "Bhai, yahan ek issue hai..."'
                    if is_hi else
                    'LANGUAGE: Simple English. Friendly tone.'
                )
                prompt = f"""You are Shiv AI — HTML coding mentor for CIWeb (ciweb.in).
{lang_instruction}
RULES:
- Max 5 lines. SHORT only.
- NEVER give full solutions. Hints only.
- Code bug → explain why + ONE hint to fix
- Missing something → guide next step
- Correct → praise + one improvement tip

CONTEXT:
Lesson: {lesson}
Code:
```html
{code}
```
User: {message}"""

            # ── Call Gemini API ──
            url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"

            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 300,
                    "temperature": 0.75
                }
            }

            response = requests.post(
                url,
                params={"key": API_KEY},
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                reply  = result["candidates"][0]["content"]["parts"][0]["text"]
                self.wfile.write(json.dumps({'reply': reply}).encode())
            else:
                self.wfile.write(json.dumps({
                    'error': f'Gemini error {response.status_code}: {response.text[:200]}'
                }).encode())

        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

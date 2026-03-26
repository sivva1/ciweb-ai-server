import requests
import json
import os
from http.server import BaseHTTPRequestHandler

ALLOWED_ORIGINS = ["https://ciweb.in", "https://www.ciweb.in"]

GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        origin = self.headers.get('Origin', '')

        if origin not in ALLOWED_ORIGINS:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Forbidden'}).encode())
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        try:
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

            API_KEY = os.environ.get('GEMINI_API_KEY', '')

            if not API_KEY:
                self.wfile.write(json.dumps({
                    'error': 'GEMINI_API_KEY not set in Vercel environment variables!'
                }).encode())
                return

            is_hi   = lang == 'hi'
            is_expl = mode == 'explain'

            if is_expl:
                prompt = message
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

            url = "https://api.groq.com/openai/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 600,
                "temperature": 0.75
            }

            response = requests.post(url, headers=headers, json=payload, timeout=15)

            if response.status_code == 200:
                result = response.json()
                reply  = result["choices"][0]["message"]["content"]
                self.wfile.write(json.dumps({'reply': reply}).encode())
            else:
                self.wfile.write(json.dumps({
                    'error': f'Groq error {response.status_code}: {response.text[:200]}'
                }).encode())

        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        origin = self.headers.get('Origin', '')
        if origin not in ALLOWED_ORIGINS:
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

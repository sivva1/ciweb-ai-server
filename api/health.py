import json
import os
from http.server import BaseHTTPRequestHandler

ALLOWED_ORIGINS = ["https://ciweb.in", "https://www.ciweb.in"]

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        origin = self.headers.get('Origin', '')

        # Health check — allow direct browser access (no origin) + allowed origins
        if origin and origin not in ALLOWED_ORIGINS:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Forbidden'}).encode())
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
        self.end_headers()

        key_set = bool(os.environ.get('GEMINI_API_KEY', ''))

        self.wfile.write(json.dumps({
            'ok':      True,
            'keySet':  key_set,
            'model':   'llama-3.1-8b-instant',
            'server':  'Vercel Serverless',
            'provider': 'Groq'
        }).encode())

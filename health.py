import json
import os
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        key_set = bool(os.environ.get('GEMINI_API_KEY', ''))

        self.wfile.write(json.dumps({
            'ok':     True,
            'keySet': key_set,
            'model':  'gemini-2.5-flash',
            'server': 'Vercel Serverless'
        }).encode())

"""WSGI entry point for PythonAnywhere. No static mappings may expose this checkout."""
import io
import json
import os
from email.message import Message
from http import HTTPStatus
from pathlib import Path

settings = Path.home() / '.config' / 'archivesguernica' / 'settings.json'
if settings.exists():
    config = json.loads(settings.read_text())
    os.environ.setdefault('ARCHIVES_ADMIN_PASSWORD', config['password'])
    os.environ.setdefault('ARCHIVES_DB', config['database'])
    for level, password in config.get('levels', {}).items():
        if level in ('2', '3', '4', '5'):
            os.environ.setdefault(f'ARCHIVES_LEVEL_{level}_PASSWORD', password)
os.environ.setdefault('ARCHIVES_SECURE_COOKIE', '1')
from server import Handler


class WSGIHandler(Handler):
    def send_response(self, code, message=None):
        self.status = f'{code} {message or HTTPStatus(code).phrase}'
        self.response_headers = []

    def send_header(self, name, value):
        self.response_headers.append((name, str(value)))

    def end_headers(self):
        pass


def application(environ, start_response):
    handler = object.__new__(WSGIHandler)
    handler.path = environ.get('PATH_INFO', '/')
    if environ.get('QUERY_STRING'):
        handler.path += '?' + environ['QUERY_STRING']
    handler.headers = Message()
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            handler.headers[key[5:].replace('_', '-')] = value
    for key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
        if environ.get(key):
            handler.headers[key.replace('_', '-')] = environ[key]
    handler.rfile = environ['wsgi.input']
    handler.wfile = io.BytesIO()
    method = environ.get('REQUEST_METHOD', 'GET')
    if method == 'GET':
        handler.do_GET()
    elif method == 'POST':
        handler.do_POST()
    else:
        handler.send(405, '{}')
    start_response(handler.status, handler.response_headers)
    return [handler.wfile.getvalue()]

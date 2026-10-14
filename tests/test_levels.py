"""Run: python3 -m unittest discover -s tests -v (temporary DB and credentials)."""
import io
import json
import os
import secrets
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory()
os.environ['ARCHIVES_DB'] = TEMP.name + '/test.db'
os.environ['ARCHIVES_ADMIN_PASSWORD'] = secrets.token_urlsafe(24)
for level in range(2, 6):
    os.environ[f'ARCHIVES_LEVEL_{level}_PASSWORD'] = secrets.token_urlsafe(24)
# Existing database must migrate without losing content, and default to level 5.
with sqlite3.connect(os.environ['ARCHIVES_DB']) as db:
    db.execute('CREATE TABLE documents (id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, body TEXT NOT NULL)')
    db.execute("INSERT INTO documents VALUES(1,'Existing','Documents','Preserved')")
import wsgi


def call(path, method='GET', data=None, cookie=None):
    env = {}; setup_testing_defaults(env)
    raw = json.dumps(data).encode() if data is not None else b''
    env.update(PATH_INFO=path, REQUEST_METHOD=method, CONTENT_TYPE='application/json', CONTENT_LENGTH=str(len(raw)))
    env['wsgi.input'] = io.BytesIO(raw)
    if cookie: env['HTTP_COOKIE'] = cookie
    result = {}
    def start(status, headers): result.update(status=int(status[:3]), headers=dict(headers))
    result['body'] = b''.join(wsgi.application(env, start))
    return result


def login(level):
    var = 'ARCHIVES_ADMIN_PASSWORD' if level == 'admin' else f'ARCHIVES_LEVEL_{level}_PASSWORD'
    response = call('/login', 'POST', {'level':str(level),'password':os.environ[var]})
    assert response['status'] == 200, response
    return response['headers']['Set-Cookie']


class Levels(unittest.TestCase):
    def test_access_matrix(self):
        admin = login('admin')
        for level in range(2, 6):
            result = call('/api/documents', 'POST', {'title':f'Level {level}','category':'Documents','body':'Secret','level':level}, admin)
            self.assertEqual(result['status'], 201)
        for level in range(2, 6):
            cookie = login(level)
            documents = json.loads(call('/api/documents',cookie=cookie)['body'])
            self.assertTrue(all(d['level'] <= level for d in documents))
            self.assertEqual({d['level'] for d in documents}, set(range(2,level+1)))
            self.assertEqual(any(d['title']=='Existing' for d in documents),level==5)
            session = json.loads(call('/api/session',cookie=cookie)['body'])
            self.assertEqual(session,{'level':level,'admin':False})
            self.assertEqual(call('/api/documents','POST',{'title':'Forged','category':'Documents','body':'Bad','level':2},cookie)['status'],403)
            self.assertEqual(call('/logout','POST',{},cookie)['status'],200)
            self.assertEqual(call('/api/documents',cookie=cookie)['status'],401)
        self.assertEqual(call('/api/documents','POST',{'title':'Bad','category':'Documents','body':'Bad','level':1},admin)['status'],400)
        self.assertEqual(call('/api/documents')['status'],401)
        self.assertEqual(call('/api/session')['status'],401)

    def test_wrong_level_or_role_cannot_authenticate(self):
        password=os.environ['ARCHIVES_LEVEL_2_PASSWORD']
        for level in ('admin','3','4','5','6'):
            self.assertEqual(call('/login','POST',{'level':level,'password':password})['status'],401)


if __name__ == '__main__': unittest.main()

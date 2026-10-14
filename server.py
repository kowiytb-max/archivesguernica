"""Private archive server. Deploy behind HTTPS; bind to loopback only."""
import os, json, secrets, time, hashlib, hmac, sqlite3, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie

ROOT = Path(__file__).parent
PASSWORD = os.environ.get('ARCHIVES_ADMIN_PASSWORD', '')
if len(PASSWORD) < 16:
    raise SystemExit('Set ARCHIVES_ADMIN_PASSWORD to a unique password of at least 16 characters.')
SALT = secrets.token_bytes(16)
KEY = hashlib.scrypt(PASSWORD.encode(), salt=SALT, n=16384, r=8, p=1)
del PASSWORD
DB = Path(os.environ.get('ARCHIVES_DB', '/workspace/archivesguernica-data/archives.sqlite3'))
DB.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
with sqlite3.connect(DB) as db:
    db.execute('CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, body TEXT NOT NULL)')
os.chmod(DB, 0o600)
SESSIONS = {}
ATTEMPTS = []
LOCK = threading.Lock()
SECURE = os.environ.get('ARCHIVES_SECURE_COOKIE', '1') != '0'
LOGIN = '''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Archives Guernica — Connexion</title><style>body{background:#101714;color:#e3e6d9;font:18px Georgia;margin:12vh auto;padding:24px;max-width:460px}input,button{box-sizing:border-box;width:100%;padding:15px;margin:12px 0;background:#17211c;color:#e3e6d9;border:1px solid #78836d}p{line-height:1.6;color:#a2ad9e}</style><h1>Archives Guernica</h1><p>Espace privé · Accès réservé à l’administrateur.</p><form id="login"><label for="password">Mot de passe</label><input id="password" type="password" autocomplete="current-password" required><button>Se connecter</button><p id="error" role="alert"></p></form><script>document.getElementById('login').onsubmit=async e=>{e.preventDefault();try{const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.getElementById('password').value})});if(r.ok)location='/';else document.getElementById('error').textContent=r.status===429?'Trop de tentatives. Réessayez dans 15 minutes.':'Connexion refusée.'}catch{document.getElementById('error').textContent='Serveur indisponible.'}}</script></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log document paths, credentials or content.
    def send(self, status, body=b'', kind='application/json', cookie=None):
        if isinstance(body, str): body=body.encode()
        self.send_response(status)
        self.send_header('Content-Type',kind+'; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(body)
    def session(self):
        try:
            c=SimpleCookie(); c.load(self.headers.get('Cookie','')); token=c['session'].value
        except (KeyError, ValueError): return None
        with LOCK:
            now=time.time()
            for key in list(SESSIONS):
                if SESSIONS[key]<now: del SESSIONS[key]
            return token if token in SESSIONS else None
    def do_GET(self):
        if self.path=='/login': return self.send(200,LOGIN,'text/html')
        if not self.session():
            if self.path.startswith('/api/'): return self.send(401,'{}')
            self.send_response(303); self.send_header('Location','/login'); self.send_header('Cache-Control','no-store'); self.end_headers(); return
        if self.path=='/': return self.send(200,(ROOT/'index.html').read_bytes(),'text/html')
        if self.path=='/api/documents':
            with sqlite3.connect(DB) as db:
                db.row_factory=sqlite3.Row
                return self.send(200,json.dumps([dict(r) for r in db.execute('SELECT * FROM documents ORDER BY id DESC')]))
        return self.send(404,'{}')
    def do_POST(self):
        # Same-origin JSON requests only; browser cross-origin forms cannot invoke mutations.
        if self.headers.get('Content-Type','').split(';')[0]!='application/json' or self.headers.get('Sec-Fetch-Site')=='cross-site': return self.send(403,'{}')
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=100000: return self.send(413,'{}')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError()
        except (ValueError,UnicodeDecodeError): return self.send(400,'{}')
        if self.path=='/login':
            with LOCK:
                now=time.time(); ATTEMPTS[:]=[t for t in ATTEMPTS if t>now-900]
                if len(ATTEMPTS)>=10: return self.send(429,'{}')
                ATTEMPTS.append(now)
            password=data.get('password','')
            if not isinstance(password,str) or len(password)>1000: return self.send(401,'{}')
            candidate=hashlib.scrypt(password.encode(),salt=SALT,n=16384,r=8,p=1)
            if not hmac.compare_digest(candidate,KEY): return self.send(401,'{}')
            token=secrets.token_urlsafe(32)
            with LOCK: SESSIONS[token]=time.time()+3600
            return self.send(200,'{}',cookie='session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'+('; Secure' if SECURE else ''))
        token=self.session()
        if not token: return self.send(401,'{}')
        if self.path=='/logout':
            with LOCK: SESSIONS.pop(token,None)
            return self.send(200,'{}',cookie='session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+('; Secure' if SECURE else ''))
        if self.path=='/api/documents':
            if not all(isinstance(data.get(k),str) and data[k].strip() for k in ('title','category','body')): return self.send(400,'{}')
            if len(data['title'])>200 or len(data['category'])>100 or len(data['body'])>50000: return self.send(400,'{}')
            with sqlite3.connect(DB) as db:
                db.execute('INSERT INTO documents(title,category,body) VALUES(?,?,?)',tuple(data[k].strip() for k in ('title','category','body')))
            return self.send(201,'{}')
        return self.send(404,'{}')

if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('PORT','8002'))),Handler).serve_forever()

"""Run once in the hosting console; never enters the password in shell history."""
from getpass import getpass
import json
import os
from pathlib import Path

root = Path.home() / '.config' / 'archivesguernica'
root.mkdir(parents=True, exist_ok=True, mode=0o700)
target = root / 'settings.json'
if target.exists():
    raise SystemExit('Configuration already exists. No changes made.')
password = getpass('Nouveau mot de passe administrateur (16 caractères minimum) : ')
if len(password) < 16:
    raise SystemExit('Mot de passe trop court. Relancez la commande.')
if password != getpass('Confirmez le mot de passe : '):
    raise SystemExit('Les mots de passe diffèrent. Relancez la commande.')
with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
    json.dump({'password': password, 'database': str(root / 'archives.sqlite3')}, stream)
print('Configuration privée enregistrée. Ne partagez pas le fichier settings.json.')

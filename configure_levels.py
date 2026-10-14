"""Set reader codes on the host without exposing them in shell history."""
import json
import os
import tempfile
from pathlib import Path
from getpass import getpass

path = Path.home() / '.config' / 'archivesguernica' / 'settings.json'
if not path.exists():
    raise SystemExit('Lancez configure_host.py avant cette commande.')
config = json.loads(path.read_text())
levels = {}
for level in range(2, 6):
    password = getpass(f'Nouveau code échelon {level} (16 caractères minimum) : ')
    if len(password) < 16:
        raise SystemExit('Code trop court. Aucun changement enregistré.')
    if password == config['password'] or password in levels.values():
        raise SystemExit('Chaque code doit être distinct. Aucun changement enregistré.')
    if password != getpass('Confirmez ce code : '):
        raise SystemExit('Les codes diffèrent. Aucun changement enregistré.')
    levels[str(level)] = password
config['levels'] = levels
fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.settings-')
try:
    with os.fdopen(fd, 'w') as stream:
        json.dump(config, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary): os.unlink(temporary)
print('Codes enregistrés. Dans Web, cliquez sur Reload pour les activer et invalider les sessions.')

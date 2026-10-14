# Archives Guernica — espace privé

Site indépendant de Guernica-Lore. Interface française, connexion administrateur, dossiers stockés dans SQLite, recherche et filtres, création et lecture de dossiers. Aucun contenu privé ni identifiant fourni dans le dépôt.

## Démarrage

Python 3.12, bibliothèque standard uniquement. Depuis la racine du dépôt :

```bash
read -rs -p 'Mot de passe administrateur (16 caractères minimum) : ' ARCHIVES_ADMIN_PASSWORD
export ARCHIVES_ADMIN_PASSWORD
python3 server.py
```

Ne pas utiliser `python -m http.server` pour ce site : cela contournerait la protection des pages. Le serveur applicatif écoute exclusivement sur 127.0.0.1:8002. Pour un test HTTP local uniquement, définir `ARCHIVES_SECURE_COOKIE=0` avant le démarrage ; en production conserver sa valeur par défaut (cookies Secure).

Variables : `ARCHIVES_ADMIN_PASSWORD` (obligatoire, secret), `ARCHIVES_DB` (chemin SQLite, défaut `/workspace/archivesguernica-data/archives.sqlite3`), `PORT` (défaut 8002), `ARCHIVES_SECURE_COOKIE` (défaut 1).

## Hébergement et limites

Placer le serveur derrière un reverse proxy HTTPS sur un hébergement avec stockage persistant, et configurer le secret dans les paramètres sécurisés de l’hébergeur. GitHub Pages ne convient pas : il ne peut pas exécuter ce serveur ni assurer cette protection. Ne jamais committer la base de données, les sauvegardes ou le mot de passe.

Un seul administrateur partagé ; sessions de 1 heure en mémoire (invalidées au redémarrage), 10 tentatives de connexion par tranche de 15 minutes pour l’ensemble du serveur. Pas de comptes individuels, MFA, récupération de mot de passe, suppression ou modification des dossiers dans cette première version. Le stockage n’est pas chiffré par l’application : prévoir disque chiffré, sauvegardes chiffrées et permissions adaptées chez l’hébergeur. L’accès au serveur ou à ses sauvegardes donne accès aux documents. Cette version n’a pas fait l’objet d’un audit de sécurité.

## Validation

Parcours testé dans Chromium : redirection sans session, refus de mot de passe erroné, API inaccessible sans session, connexion, création de dossier, recherche insensible aux accents, lecture, rendu du contenu comme texte, fermeture au clavier, état sans résultat et déconnexion. Tests exécutés avec base temporaire et secret aléatoire ; aucune donnée de test conservée dans la base de production.

## PythonAnywhere

1. Dans une console Bash : `git clone https://github.com/kowiytb-max/archivesguernica.git`, puis `cd archivesguernica` et `python3 configure_host.py`. Le mot de passe est saisi sans affichage et conservé hors du dépôt avec des permissions privées.
2. Web → Add a new web app → domaine gratuit → Manual configuration → Python 3.12 (ou version compatible disponible).
3. Ouvrir le fichier de configuration WSGI proposé dans Web. Remplacer son contenu par le code suivant en remplaçant USERNAME par le nom exact du compte :

```python
import sys
project = '/home/USERNAME/archivesguernica'
if project not in sys.path:
    sys.path.insert(0, project)
from wsgi import application
```

4. Ne configurer aucun « Static files » pour ce dépôt : toutes les pages doivent passer par l’authentification. Activer « Force HTTPS » si disponible, puis Reload. Utiliser uniquement l’adresse HTTPS affichée dans l’onglet Web.
5. Vérifier la redirection vers la connexion, l’ajout d’un dossier de test et la déconnexion. Depuis une fenêtre privée, vérifier que `/api/documents` refuse l’accès.

La base et la configuration sont dans `~/.config/archivesguernica/`, hors du dépôt. Ne pas les partager. Faire des sauvegardes privées. Les sessions et la limitation des tentatives sont en mémoire : cette version suppose un seul processus WSGI et invalide les sessions après rechargement. Vérifier les conditions de renouvellement et les quotas affichés par PythonAnywhere. Les tests locaux ne prouvent pas le déploiement distant. L’hébergeur et l’administrateur du compte peuvent accéder au stockage ; il n’est pas chiffré par l’application.

## Échelons 2 à 5

Les codes d’échelon sont des accès **en lecture seule**, distincts de l’administration. L’accès est cumulatif : 2 voit les dossiers 2 ; 3 voit 2 et 3 ; 4 voit 2 à 4 ; 5 voit tous les dossiers. Le filtrage est appliqué côté serveur avant tout envoi au navigateur. Seul l’administrateur crée et classe les documents. Les documents existants sont conservés et classés automatiquement au niveau 5 lors du premier démarrage de cette version.

Sur PythonAnywhere, dans Bash :

```bash
cd ~/archivesguernica
git pull --ff-only
python3 configure_levels.py
```

Saisir puis confirmer les quatre codes distincts (au moins 16 caractères chacun). La saisie est masquée. Le script préserve le mot de passe administrateur et les autres paramètres existants et remplace uniquement les codes d’échelon après validation de toutes les saisies. Il écrit atomiquement la configuration privée hors du dépôt. Puis **Web → Reload** pour activer les codes et invalider toutes les sessions existantes. Une rotation future utilise la même commande. Aucun code par défaut n’est inclus.

Pour un démarrage local sans WSGI, fournir `ARCHIVES_LEVEL_2_PASSWORD`, `ARCHIVES_LEVEL_3_PASSWORD`, `ARCHIVES_LEVEL_4_PASSWORD`, `ARCHIVES_LEVEL_5_PASSWORD` en variables secrètes. Un échelon sans code configuré est inaccessible. Ce sont des codes partagés par groupe, sans identification individuelle ni révocation d’une seule personne. La limite des tentatives est commune aux accès.

Validation : `python3 -m unittest discover -s tests -v` vérifie la migration d’une ancienne base, la matrice complète d’accès cumulatif, les refus de création par les lecteurs, les mauvais échelons et la déconnexion. Un parcours Chromium a également vérifié la création et la classification administrateur, la connexion au niveau 2, l’absence de dossier de niveau 5 et la lecture autorisée.

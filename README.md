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

# Real-Time User Session Activity Tracking (Django + Redis)

Backend Django qui utilise Redis comme base NoSQL principale (hash, set, sorted set, TTL) pour suivre en temps réel les sessions et l’activité des utilisateurs.

## Fonctionnalités
- Création de session à la connexion (hash + TTL)
- Mise à jour du `last_activity` à chaque action
- Expiration automatique après inactivité
- Gestion des utilisateurs en ligne (set)
- Classement optionnel par activité (sorted set)
- Endpoints API REST pour dashboard en temps réel

## Prérequis
- Python 3.10+
- Redis en local ou distant (REDIS_URL)

## Installation rapide
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Variables d’environnement utiles
- `REDIS_URL` (par défaut `redis://localhost:6379/0`)
- `SESSION_TTL_SECONDS` (par défaut `1800`)
- `ACTIVITY_SCORE_ENABLED` (1/0, par défaut 1)
- `DJANGO_DEBUG` (1/0, par défaut 1)
- `DJANGO_ALLOWED_HOSTS` (ex: `localhost,127.0.0.1`)

## Lancer le serveur
```bash
python manage.py runserver
```

## Endpoints (tous sous `/api/`)
- `POST /api/sessions/login` body `{ "user_id": "u1" }`
- `POST /api/sessions/activity` body `{ "session_id": "<uuid>" }`
- `POST /api/sessions/logout` body `{ "session_id": "<uuid>" }`
- `GET  /api/sessions/<session_id>`
- `GET  /api/dashboard/summary`
- `GET  /api/dashboard/leaderboard?limit=50`

## Structure Redis
- `HASH session:{session_id}` : user_id, login_time, last_activity, status
- `STRING session:{session_id}:expire` : TTL pour expiration
- `SET online_users` : utilisateurs en ligne
- `SORTED SET user_activity_score` : score activité (optionnel)

## Notes
- Pas de modèles SQL : Redis est le store principal.
- Pour des tests unitaires, moquez Redis (lib `fakeredis` conseillée).

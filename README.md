# Gestion de Tickets en Temps Réel (Django + Redis)

Backend Django qui utilise Redis comme base NoSQL principale (LIST, HASH, STRING+TTL) pour gérer une file de tickets (poste) en temps réel : prise de ticket, appel, clôture, ouverture/fermeture quotidienne avec reset auto.

## Fonctionnalités
- Prise de ticket (FIFO via LIST), métadonnées en HASH, numéro auto par jour
- Appel du ticket suivant, clôture du ticket en cours
- Ouverture/fermeture de journée (STRING de jour + TTL pour reset quotidien)
- Logs des actions (start/end/take/call/finish) stockés dans Redis
- Pages :
  - Public : `/api/tickets/public` (prendre un ticket, voir son numéro et l’attente)
  - Staff : `/api/tickets/staff` (Start/End Day, Call Next, Finish Current, stats live)
  - Dashboard : `/api/dashboard` (statuts, file, logs et graphique actions en temps réel)

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
- `DJANGO_DEBUG` (1/0, par défaut 1)
- `DJANGO_ALLOWED_HOSTS` (ex: `localhost,127.0.0.1`)

## Lancer le serveur
```bash
python manage.py runserver
```

## Endpoints (tous sous `/api/`)
- `GET  /api/dashboard` (page dashboard tickets)
- `GET  /api/tickets/public` (page publique)
- `GET  /api/tickets/staff` (page staff)
- `POST /api/tickets/start-day`
- `POST /api/tickets/end-day`
- `POST /api/tickets/take`
- `GET  /api/tickets/status`
- `POST /api/tickets/call-next`
- `POST /api/tickets/finish-current`
- `GET  /api/tickets/snapshot` (statuts + logs)

## Structure Redis
- `STRING tickets:{YYYY-MM-DD}:day` : marqueur de jour (TTL jusqu’à minuit)
- `STRING tickets:{YYYY-MM-DD}:counter` : compteur de tickets du jour
- `LIST   tickets:{YYYY-MM-DD}:queue` : file FIFO des tickets
- `STRING tickets:{YYYY-MM-DD}:current` : ticket en cours
- `HASH   tickets:{YYYY-MM-DD}:ticket:{n}` : détails ticket (status, time, service)
- `LIST   tickets:{YYYY-MM-DD}:logs` : logs des actions (start/end/take/call/finish) max 50

## Notes
- Pas de modèles SQL : Redis est le store principal.
- Pour des tests unitaires, moquez Redis (lib `fakeredis` conseillée).

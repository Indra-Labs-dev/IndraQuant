# IndraQuant — AI Quantitative Trading & Market Intelligence Platform

## Description

IndraQuant est une plateforme de recherche quantitative et d'analyse des marchés financiers basée sur l'intelligence artificielle. Elle collecte, traite et analyse des données de marché en temps réel afin de produire des prévisions probabilistes, des analyses techniques avancées, des évaluations du risque et des recommandations d'aide à la décision. Grâce à une architecture modulaire et à des modèles d'IA multiples, la plateforme permet de comparer les performances des algorithmes, d'effectuer des backtests, du paper trading et d'expliquer chaque prédiction de manière transparente.

## Démarrage (développement, Kali Linux natif)

Prérequis : Python 3.12+, Node.js LTS, et le stack partagé [Homelab](~/Homelab)
(PostgreSQL + Redis, réseau Docker `indralabs-network`) démarré via
`~/Homelab/scripts/start.sh`.

```bash
# Base de données : créer la base dédiée sur le Postgres du Homelab (une seule fois)
~/Homelab/scripts/create-database.sh indraquant
# En cas d'erreur \gexec (bug connu du script), solution de repli :
# docker exec indralabs-postgres psql -U indra_admin -d postgres -c 'CREATE DATABASE indraquant OWNER indra_admin'

# Backend — conteneurisé, rejoint indralabs-network (voir docker-compose.yml)
cp backend/.env.example backend/.env   # puis renseigner DATABASE_URL / REDIS_URL
# (identifiants a copier depuis ~/Homelab/.env : POSTGRES_PASSWORD, REDIS_PASSWORD)
docker compose up -d --build
curl http://127.0.0.1:8100/api/v1/health

# Frontend — natif, http://localhost:3000
cd frontend
npm install
npm run dev
```

Assistant IA et analyse de sentiment (Ollama local) : Ollama doit écouter sur
`0.0.0.0` (pas seulement `127.0.0.1`) pour être joignable depuis le conteneur backend
via `host.docker.internal` — voir `OLLAMA_HOST` dans la configuration du service Ollama.

Le backend tourne en conteneur Docker Compose (`docker-compose.yml`, service `backend`),
sur le réseau externe `indralabs-network` du Homelab — voir `RAPPORT_IMPLEMENTATION.md`
pour le détail des décisions d'architecture. Pour le développement actif du backend sans
reconstruire l'image à chaque changement, il reste possible de le lancer nativement :

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# DATABASE_URL/REDIS_URL doivent alors utiliser localhost au lieu de postgres/redis
uvicorn src.main:app --reload --port 8100
```


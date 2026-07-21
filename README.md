# IndraQuant — AI Quantitative Trading & Market Intelligence Platform

## Description

IndraQuant est une plateforme de recherche quantitative et d'analyse des marchés financiers basée sur l'intelligence artificielle. Elle collecte, traite et analyse des données de marché en temps réel afin de produire des prévisions probabilistes, des analyses techniques avancées, des évaluations du risque et des recommandations d'aide à la décision. Grâce à une architecture modulaire et à des modèles d'IA multiples, la plateforme permet de comparer les performances des algorithmes, d'effectuer des backtests, du paper trading et d'expliquer chaque prédiction de manière transparente.

## Démarrage (développement, PowerShell)

Prérequis : Python 3.12+, Node.js LTS, MySQL/MariaDB local, et Microsoft Garnet comme cache compatible Redis (voir `docs/07-decisions-architecture.md`, ADR-010 à 012).

```powershell
# Cache (Garnet) — à lancer si pas déjà démarré (winget install Microsoft.Garnet.DN8)
& "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Microsoft.Garnet.DN8_Microsoft.Winget.Source_8wekyb3d8bbwe\net8.0\GarnetServer.exe" --port 6379
```

```powershell
# Backend — http://127.0.0.1:8100/api/v1/health
# (port 8100 : le port 8000 est occupé par un service Windows sur cette machine)
cd backend
Copy-Item .env.example .env   # puis renseigner DATABASE_URL / REDIS_URL
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn src.main:app --reload --port 8100

# Frontend — http://localhost:3000
cd frontend
npm install
npm run dev
```


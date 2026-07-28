# Image backend IndraQuant - rejoint le reseau externe `indralabs-network` du
# Homelab pour atteindre Postgres/Redis par nom de service (voir
# docker-compose.yml a la racine du projet).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8100

# Applique les migrations Alembic avant de demarrer (base locale mono-utilisateur,
# pas de coordination multi-instance a gerer). --loop uvloop : boucle asyncio plus
# rapide (gain net et sans risque). Un seul worker (pas de --workers) : les 5
# taches de fond et le cache d'instruments en memoire (SqlAlchemyInstrumentRepository)
# sont process-local - plusieurs workers dupliqueraient les taches de fond et
# fragmenteraient ce cache entre processus.
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8100 --loop uvloop"]

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
# pas de coordination multi-instance a gerer).
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8100"]

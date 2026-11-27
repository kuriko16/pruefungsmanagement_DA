# Lokales Image für die Weboberfläche (keine Cloud, Daten bleiben im Ordner data/)
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-calc fonts-crosextra-carlito && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY webapp webapp
COPY tools tools
COPY vorlagen vorlagen
ENV PM_DB=/app/data/pruefung.db PM_HOST=0.0.0.0
EXPOSE 9094
# DEMO=1: beim ersten Start erfundene Demodaten laden, wenn noch keine Datenbank existiert
CMD ["sh", "-c", "if [ \"$DEMO\" = \"1\" ] && [ ! -f \"$PM_DB\" ]; then python tools/demodaten.py --db; fi; python webapp/app.py"]

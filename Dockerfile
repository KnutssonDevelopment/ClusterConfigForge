# Brug en letvægts Python-image
FROM python:3.14-slim

# Sæt arbejdsmappen i containeren
WORKDIR /app

# Installer uv (siden du bruger det til dine lock-filer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Kopier lock-filer og requirements
COPY pyproject.toml uv.lock ./

# Installer afhængigheder (uden at oprette en venv, da containeren ER miljøet)
RUN uv pip install --system -r pyproject.toml

# Kopier resten af koden
COPY . .

# Fortæl Docker hvilken port appen bruger
EXPOSE 5000

# Start appen med gunicorn (husk at tilføje gunicorn til dine requirements)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

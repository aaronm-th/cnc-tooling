FROM python:3.11-slim


# Systemabhängigkeiten für WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpango1.0-dev \
    libgdk-pixbuf-xlib-2.0-0 \
    libgdk-pixbuf-xlib-2.0-dev \
    libffi-dev \
    libgirepository1.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*


# Arbeitsverzeichnis
WORKDIR /app
ENV XDG_CACHE_HOME=/tmp


# Non-root User erstellen
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser


# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY . .

# Besitzer ändern
RUN chown -R appuser:appgroup /app

# Wechsel zu non-root User
USER appuser

EXPOSE 8000

# Default-Command (wird von docker-compose überschrieben)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user. The SQLite database can't be created in the
# root-owned /app, so give the user a dedicated, writable data directory and
# point DATABASE_URL at it. docker-compose mounts a named volume here so the
# database survives container recreation.
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data
USER appuser
ENV DATABASE_URL=sqlite:////app/data/debates.db

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

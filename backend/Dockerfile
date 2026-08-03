FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the package and its dependencies first — this layer is only
# rebuilt when pyproject.toml or the application package changes.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# Tests and the rest of the project; in development the source is bind-mounted
# over /app by Docker Compose and uvicorn reloads on change.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

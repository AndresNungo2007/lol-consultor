FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir .

ENV LOL_CACHE_DIR=/data/.lol_cache
VOLUME ["/data"]

EXPOSE 8050

CMD ["python", "scripts/run_dash.py"]

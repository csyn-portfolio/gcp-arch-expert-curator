FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY src /app/src
COPY config /app/config

RUN pip install --no-cache-dir .

# After pip install, the package lives in site-packages and the dev-tree
# config resolution (Path(__file__).parent.parent.parent / "config") points
# at site-packages's grandparent — wrong. Pin the runtime config dir.
ENV CURATOR_CONFIG_DIR=/app/config

ENTRYPOINT ["python", "-m", "curator.main"]

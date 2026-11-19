FROM python:3.14-slim-trixie

# Install system dependencies
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/

# Set up a nonroot user for tightened security
RUN adduser --disabled-password nonroot && \
    mkdir -p /app/tmp && \
    chown -R nonroot:nonroot /app
WORKDIR /app

# Download GADM database
RUN apt-get update && apt-get install -y wget unzip \
      && mkdir -p src/gadm \
      && wget -O /tmp/gadm.zip https://geodata.ucdavis.edu/gadm/gadm4.1/gadm_410-gpkg.zip \
      && unzip /tmp/gadm.zip -d /tmp/gadm \
      && mv /tmp/gadm/*.gpkg src/gadm/gadm.gpkg \
      && rm -rf /tmp/gadm.zip /tmp/gadm \
      && chown -R nonroot:nonroot src/gadm

COPY --chown=nonroot:nonroot . .

# Set up Python environment
ENV UV_PYTHON=/usr/local/bin/python \
    UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY src src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Run
USER nonroot
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 9999
CMD ["uvicorn", "src.agent:create_app", "--factory", "--host", "0.0.0.0", "--port", "9999"]

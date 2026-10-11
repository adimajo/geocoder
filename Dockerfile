# syntax=docker/dockerfile:1

# Both images can be replaced, e.g. to pull from an internal registry
ARG DOCKER_REGISTRY=""
ARG BASE_IMAGE=python:3.12-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.9

FROM ${UV_IMAGE} AS uv

FROM ${DOCKER_REGISTRY}${BASE_IMAGE} AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# dependencies first: this layer is cached until pyproject.toml / uv.lock change
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra api --extra s3 --no-install-project
COPY geocoder geocoder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra api --extra s3 --no-editable


FROM ${DOCKER_REGISTRY}${BASE_IMAGE}
ARG VERSION=dev
ARG REVISION=unknown
LABEL org.opencontainers.image.title="geocoder" \
      org.opencontainers.image.description="Address search engine for France, based on the BAN" \
      org.opencontainers.image.source="https://github.com/adimajo/geocoder" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"

# the code is owned by root and read-only for the service; only /data is writable
RUN useradd --system --uid 10001 --no-create-home geocoder \
    && mkdir /data && chown geocoder /data
COPY --from=builder /app/.venv /app/.venv
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    GEOCODER_DATA_DIR=/data \
    GEOCODER_HOST=0.0.0.0 \
    GEOCODER_PORT=8000
VOLUME /data
EXPOSE 8000
USER geocoder

# The first start downloads the BAN and builds the database (the server only listens afterwards): give it time.
HEALTHCHECK --interval=30s --timeout=5s --start-period=2h --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['GEOCODER_PORT'] + '/version', timeout=3)"]

ENTRYPOINT ["docker-entrypoint.sh"]

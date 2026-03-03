FROM ghcr.io/astral-sh/uv:python3.14-alpine@sha256:2772966529822c47102b21a7ed82916893f2c9fe27ee6dc2766b681e0a57a3f0

WORKDIR /app

ENV UV_NO_DEV=1

COPY uv.lock pyproject.toml ./

RUN uv sync --locked

COPY . .

CMD ["uv", "run", "--no-sync", "-m", "byte_bot"]
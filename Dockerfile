FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y git cron && rm -rf /var/lib/apt/lists/*

COPY . ./CROUStillant

WORKDIR /CROUStillant

RUN uv sync --frozen

RUN crontab crontab

CMD ["cron", "-f"]

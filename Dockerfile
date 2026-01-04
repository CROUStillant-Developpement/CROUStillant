FROM python:3.12.10-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apk add --no-cache git

COPY . ./CROUStillant

WORKDIR /CROUStillant

RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev cargo make

RUN uv sync --frozen

RUN apk del gcc musl-dev python3-dev libffi-dev cargo make

RUN crontab crontab

CMD ["crond", "-f", "-L", "/dev/stdout"]

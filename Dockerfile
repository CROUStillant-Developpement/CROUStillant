FROM python:3.12.7-alpine3.20

RUN apk add --no-cache git

COPY . ./CROUStillant

WORKDIR /CROUStillant

RUN pip install --no-cache-dir -r requirements.txt

RUN crontab crontab

CMD ["crond", "-f"]

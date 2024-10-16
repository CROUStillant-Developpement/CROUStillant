FROM python:3.12.7-alpine3.20

COPY . ./CROUStillant

WORKDIR /CROUStillant

RUN pip install -r requirements.txt

RUN crontab crontab

CMD ["crond", "-f"]

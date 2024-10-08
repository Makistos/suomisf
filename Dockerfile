FROM --platform=$BUILDPLATFORM python:3.8.0 AS builder

WORKDIR /app
COPY ./requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

ENV FLASK_RUN_HOST 0.0.0.0

EXPOSE 5005

CMD ["flask", "run"]

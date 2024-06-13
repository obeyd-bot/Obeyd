FROM python:3-slim

RUN apt-get update && apt-get install -y make

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /app
COPY . .

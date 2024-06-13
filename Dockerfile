FROM python:3

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /app
COPY . .

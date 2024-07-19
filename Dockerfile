FROM python:3

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /app
COPY . .

ENV PYTHONPATH=.

CMD ["bash", "-c", "python3 obeyd/db.py && python3 obeyd/app.py"]

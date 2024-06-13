export PYTHONPATH = .

.PHONY: db-upgrade db-revision start-server clean

db-upgrade:
	alembic upgrade head

db-revision:
	alembic revision --autogenerate

start-server:
	python3 obeyd/app.py

clean:
	find . -type d -name "__pycache__" | xargs rm -r

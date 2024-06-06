export PYTHONPATH = .

.PHONY: db-upgrade db-revision start-server start-celery-worker start-admin-panel clean

db-upgrade:
	alembic upgrade head

db-revision:
	alembic revision --autogenerate

start-server:
	python3 obeyd

start-celery-worker:
	celery -A obeyd.tasks worker --loglevel=INFO

start-admin-panel:
	python3 obeyd/admin.py

clean:
	find . -type d -name "__pycache__" | xargs rm -r

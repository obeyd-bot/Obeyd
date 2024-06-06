.PHONY: db-upgrade db-revision start-server start-celery-worker start-admin-panel

db-upgrade:
	alembic upgrade head

db-revision:
	alembic revision --autogenerate

start-server:
	python3 app.py

start-celery-worker:
	celery -A tasks worker --loglevel=INFO

start-admin-panel:
	python3 admin.py

export PYTHONPATH = .

.PHONY: db-upgrade start-server start-admin-server clean

db-upgrade:
	python3 obeyd/db.py

start-server:
	python3 obeyd/app.py

start-admin-server:
	python3 obeyd/admin.py

clean:
	find . -type d -name "__pycache__" | xargs rm -r

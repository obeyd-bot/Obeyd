export PYTHONPATH = .

.PHONY: db-upgrade start-server clean

db-upgrade:
	python3 obeyd/db.py

start-server:
	python3 obeyd/app.py

clean:
	find . -type d -name "__pycache__" | xargs rm -r

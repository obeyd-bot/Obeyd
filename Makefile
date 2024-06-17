export PYTHONPATH = .

.PHONY: db-upgrade start-server start-admin-server push-master clean

db-upgrade:
	python3 obeyd/db.py

start-server:
	python3 obeyd/app.py

start-admin-server:
	python3 obeyd/admin.py

push-master:
	git checkout master
	git rebase devel
	git push origin master

clean:
	find . -type d -name "__pycache__" | xargs rm -r

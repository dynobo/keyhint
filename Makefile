init:
	pip install -r requirements-dev.txt

test:
	pytest tests

run:
	.venv/bin/python -m pyshortcut
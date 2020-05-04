init:
	rm -rf ./.venv
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt

test:
	.venv/bin/pytest tests

run:
	.venv/bin/python -m keyhint

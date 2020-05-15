init:
	rm -rf ./.venv
	rm ~/.config/keyhint/*
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt

reset_config:
	rm ~/.config/keyhint/*

test:
	.venv/bin/pytest tests

lint:
	.venv/bin/pylama

run:
	.venv/bin/python -m keyhint

package:
	rm -rf build dist
	python setup.py sdist bdist_wheel
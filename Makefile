colon := :
$(colon) := :

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
	.venv/bin/python setup.py sdist bdist_wheel
	.venv/bin/twine check dist/*

upload_test:
	rm -rf build dist
	.venv/bin/python setup.py sdist bdist_wheel
	.venv/bin/twine check dist/*
	.venv/bin/twine upload --repository-url=https$(:)//test.pypi.org/legacy/ dist/*

upload_final:
	rm -rf build dist
	.venv/bin/python setup.py sdist bdist_wheel
	.venv/bin/twine check dist/*
	.venv/bin/twine upload dist/*
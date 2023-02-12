SHELL := /bin/bash

.ONESHELL:
clean:
	rm -rf ./app.onefile-build
	rm -rf ./app.build
	rm -rf ./app.dist

.ONESHELL:
build:
	python -m nuitka \
		--onefile \
		--assume-yes-for-downloads \
		--enable-plugin=no-qt \
		--include-data-dir=keyhint/config=keyhint/config \
		--include-data-dir=keyhint/resources=keyhint/resources \
		--linux-icon=keyhint/resources/keyhint.svg \
		--file-version=0.2.4 \
		--product-name=KeyHint \
		-o KeyHint-0.2.4-x86_64.AppImage \
		keyhint/app.py

clean-build: clean build

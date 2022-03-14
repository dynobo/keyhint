SHELL := /bin/bash

.ONESHELL:
clean:
	rm -rf ./app.build
	rm -rf ./app.dist

.ONESHELL:
build:
	python -m nuitka \
		--onefile \
		--assume-yes-for-downloads \
		--enable-plugin=anti-bloat \
		--enable-plugin=gi \
		--include-data-dir=keyhint/config=keyhint/config \
		--include-data-dir=keyhint/resources=keyhint/resources \
		-o keyhint.bin \
		keyhint/app.py 

clean-build: clean build
	
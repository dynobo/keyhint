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
		-o KeyHint-0.2.3-x86_64.AppImage \
		keyhint/app.py 

clean-build: clean build
	
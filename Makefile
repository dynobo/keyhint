SHELL := /bin/bash

.ONESHELL:
build:
	rm -rf ./linux
	briefcase create --no-input
	briefcase build
	briefcase package
	cd ./linux
	FILE_NAME=$$(ls -t ./*.AppImage | head -1)
	$$FILE_NAME --appimage-extract
	rm ./squashfs-root/usr/lib/libcairo.so.2
	rm ./$$FILE_NAME
	appimagetool -v ./squashfs-root ./$$FILE_NAME
	rm -rf ./squashfs-root
	cd ..

run: 
	briefcase run
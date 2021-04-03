SHELL := /bin/bash

.ONESHELL:
clean:
	rm -rf ./linux
	mkdir linux
	wget https://github.com/AppImage/AppImageKit/releases/download/12/appimagetool-x86_64.AppImage -O ./linux/appimagetool
	chmod +x ./linux/appimagetool

.ONESHELL:
build:
	briefcase create --no-input
	briefcase build
	briefcase package
	cd ./linux
	FILE_NAME=$$(ls -t ./*.AppImage | head -1)
	$$FILE_NAME --appimage-extract
	rm ./squashfs-root/usr/lib/libcairo.so.2
	rm ./$$FILE_NAME
	./appimagetool -v ./squashfs-root ./$$FILE_NAME
	rm -rf ./squashfs-root
	cd ..

clean-build: clean build

run: 
	briefcase run

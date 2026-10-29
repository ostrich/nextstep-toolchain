CC = nextstep-gcc
ARCHS = -arch m68k -arch i386 -arch hppa -arch sparc
CFLAGS = -O2

all: hello
hello: hello.c
	$(CC) $(ARCHS) $(CFLAGS) hello.c -o hello
stage: hello
	mkdir -p stage/usr/local/bin
	cp hello stage/usr/local/bin/hello
	chmod 755 stage/usr/local/bin/hello
package: stage
	nextpkg build package.json --output dist
.PHONY: all stage package

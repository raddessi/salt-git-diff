build:
	docker build --force-rm -t tomologic/$(shell basename $(CURDIR)) .

test:
	docker run --rm -i -v $(shell pwd):/mnt/git tomologic/salt-git-diff -o text

build:
	docker build --force-rm -t tomologic/$(shell basename $(CURDIR)) .

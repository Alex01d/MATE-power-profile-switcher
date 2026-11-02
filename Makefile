PYTHON ?= /usr/bin/python3

.PHONY: check install uninstall

check:
	$(PYTHON) -m unittest discover -s tests -v
	for script in install.sh uninstall.sh configure-tuned.sh; do bash -n "$$script" || exit; done

install:
	bash ./install.sh

uninstall:
	bash ./uninstall.sh

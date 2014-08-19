define green
	@tput setaf 2
	@tput bold
	@echo $1
	@tput sgr0
endef
in_venv=venv/bin/activate

.PHONY: default

default: venv flake8 unit_tests feature_tests
	$(call green,"[Build successful]")

all: default local_device_tests
	$(call green,"[Build with device tests successful]")

venv: venv/bin/activate
venv/bin/activate: requirements.dev.txt requirements.prod.txt
	test -d venv || virtualenv venv
	. venv/bin/activate; pip install --upgrade 'pip>=1.4';
	. venv/bin/activate; pip install -r requirements.dev.txt
	touch venv/bin/activate
	$(call green,"[Making venv successful]")

.PHONY: flake8
flake8: venv
	. $(in_venv); flake8 app.py
	$(call green,"[Static analysis (flake8) successful]")

.PHONY: unit_tests
unit_tests:
	. $(in_venv); nosetests -q --with-xunit --exe --cover-erase\
		--with-coverage --cover-package=app
	$(call green,"[Unit tests successful]")

.PHONY: clean
clean:
	rm -Rf venv

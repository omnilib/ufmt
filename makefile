SRCS:=ufmt
EXTRAS:=dev,docs,ruff

ifeq ($(OS),Windows_NT)
    ACTIVATE:=.venv/Scripts/activate
else
    ACTIVATE:=.venv/bin/activate
endif

UV:=$(shell uv --version)
ifdef UV
	VENV:=uv venv
	PIP:=uv pip
else
	VENV:=python -m venv
	PIP:=python -m pip
endif

.venv:
	$(VENV) .venv

venv: .venv
	source $(ACTIVATE) && make install
	echo 'run `source $(ACTIVATE)` to use virtualenv'

install:
	$(PIP) install -Ue .[$(EXTRAS)]

format:
	python -m ufmt format $(SRCS)

lint:
	python -m mypy --install-types --non-interactive $(SRCS)
	python -m flake8 $(SRCS)
	python -m ufmt diff $(SRCS)

test:
	python -m coverage run -m $(SRCS).tests
	python -m coverage combine
	python -m coverage report

deps:
	python -m pessimist -c 'python -m $(SRCS).tests' --requirements= --fast .

.PHONY: benchmark
benchmark:
	python -m $(SRCS).tests.benchmark

.PHONY: html
html: .venv README.md docs/*.rst docs/conf.py
	source $(ACTIVATE) && sphinx-build -ab html docs html

clean:
	rm -rf build dist html README MANIFEST *.egg-info .mypy_cache

distclean: clean
	rm -rf .venv

SRCS:=ufmt
ifeq ($(OS),Windows_NT)
    ACTIVATE:=.venv/Scripts/activate
else
    ACTIVATE:=.venv/bin/activate
endif

.venv:
	python -m venv .venv
	source $(ACTIVATE) && make setup dev
	echo 'run `source $(ACTIVATE)` to use virtualenv'

venv: .venv

dev:
	python -m pip install -e .

setup:
	python -m pip install -U pip
	python -m pip install -Ur requirements-dev.txt

release: lint test clean
	flit publish

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

.PHONY: html
html: .venv README.md docs/*.rst docs/conf.py
	source $(ACTIVATE) && sphinx-build -ab html docs html

clean:
	rm -rf build dist html README MANIFEST *.egg-info .mypy_cache

distclean: clean
	rm -rf .venv

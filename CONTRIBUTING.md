# Contributing to µfmt

## Setup

Create a fresh development enviroment, and install the
appropriate tools and dependencies:

    $ make venv
    $ source .venv/bin/activate


## Validate

With the virtualenv activated, run the tests and linters:

    $ make test lint


## Submit

Before submitting a pull request, please ensure
that you have done the following:

* Documented changes or features in README.md
* Added appropriate license headers to new files
* Written or modified tests for new functionality
* Used `make format` to format code appropriately
* Validated and tested code with `make test lint`

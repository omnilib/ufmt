User Guide
==========

Configuration
-------------

All configuration for µfmt is done via the :file:`pyproject.toml` file.  This is the
same file that is used for configuring black and µsort.

Specifying options requires adding them to the ``tool.ufmt`` namespace,
following this example:

.. code-block:: toml

    [tool.ufmt]
    excludes = [...]

Options available are described as follows:

.. attribute:: excludes
    :type: List[str]

    Optional list of supplemental patterns of file paths to exclude from formatting.
    Each element must be a string following "gitignore" style matching rules. These
    excludes will be combined with the contents of the project root's :file:`.gitignore`
    file, and any file or directory path that matches any of these patterns will not be
    formatted.

    .. code-block:: toml
        :caption: pyproject.toml

        [tool.ufmt]
        excludes = [
            "fizz.py",
            "foo/",
        ]

    This configuration would ignore the following paths when formatting a project:

    * :file:`fizz.py`
    * :file:`bar/fizz.py`
    * :file:`foo/buzz.py`
    * :file:`foo/bar/baz.py`


Integrations
------------

µfmt supports integrations with the following tools and services:

- `GitHub Actions`_
- `pre-commit`_


GitHub Actions
~~~~~~~~~~~~~~

µfmt can be run as part of a project's existing Actions workflow, adding the following
snippet to the ``steps`` section of a job:

.. code-block:: yaml

    steps:
      - uses: omnilib/ufmt@action-v1
        with:
          path: <PATH TO CHECK>

This can also be added as a standalone workflow. If a ``setup-python`` step is not
already used, the :attr:`python-version` input must be specified:

.. code-block:: yaml
    :caption: .github/workflows/ufmt.yml

    name: "µfmt"
    on:
      push:
        branches:
          - main
      pull_request:
    jobs:
      check:
        runs-on: ubuntu-latest
        steps:
          - name: Check formatting
            uses: omnilib/ufmt@action-v1
            with:
              path: <PATH TO CHECK>
              python-version: "3.x"

The following inputs are supported to change the way the Action is performed, and
must be specified as part of the ``with`` section of the job step:

.. attribute:: path (required)

    One or more paths (relative to the repository root) that should be checked.

.. attribute:: version

    The version of µfmt to install and use when checking formatting.

    Defaults to installing the latest version, or whatever version is already installed
    by previous steps in the workflow.

.. attribute:: black-version

    The version of black to install and use when checking formatting.

    Defaults to installing the latest version, or whatever version is already installed
    by previous steps in the workflow.

.. attribute:: python-version

    When specified, the Github ``actions/setup-python`` action will be triggered, with
    the given version string as the desired version of Python to use. Using ``"3.x"``
    is recommended, to run µfmt using the latest stable release of Python.

    See the `setup-python advanced usage`__ for supported values.

    .. __: https://github.com/actions/setup-python/blob/main/docs/advanced-usage.md#using-the-python-version-input

.. attribute:: usort-version

    The version of µsort to install and use when checking formatting.

    Defaults to installing the latest version, or whatever version is already installed
    by previous steps in the workflow.


pre-commit
~~~~~~~~~~

µfmt can format your project automatically before every commit as part of a project's
`pre-commit <https://pre-commit.com>`_ hook. Add the following to the
``.pre-commit-config.yaml`` file:

.. code-block:: yaml

    - repo: https://github.com/omnilib/ufmt
      rev: v1.3.3
      hooks:
        - id: ufmt

.. attribute:: additional_dependencies

    Preferred versions of black and µsort should be provided for consistent results.
    By default, µfmt will format using the latest versions of black and µsort.

    .. code-block:: yaml

        - repo: https://github.com/omnilib/ufmt
          hooks:
            - id: ufmt
              additional_dependencies:
                - black == 22.6.0
                - usort == 1.0.3

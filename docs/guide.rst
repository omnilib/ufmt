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
    :value: []

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

**Experimental** options may be removed or unsupported in future releases:

.. attribute:: formatter
    :type: str
    :value: "black"

    **Experimental** option to use an alternative formatter instead of black.
    Changing this selection is likely to generate different formatting results
    as compared to black, especially depending on available or pinned versions
    of each formatter in µfmt's environment.

    .. code-block:: toml
      :caption: pyproject.toml

      [tool.ufmt]
      formatter = "ruff"

    See :class:`~ufmt.types.Formatter` for list of supported choices.


Integrations
------------

µfmt supports integrations with the following tools and services:

- `GitHub Actions`_
- `pre-commit`_
- `Visual Studio Code`_


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

For consistent and predictable behavior in CI, it is recommended to pin your version
of black and µsort. These can be individually configured in the workflow (see Options),
but prefer using a requirements file with pinned versions, and the µfmt action can
install those dependencies if they aren't already installed by a previous step:

.. code-block::
    :caption: requirements-fmt.txt

    black==22.6.0
    usort==1.0.4

.. code-block:: yaml
    :caption: .github/workflows/ufmt.yml

    steps:
      - uses: omnilib/ufmt@action-v1
        with:
          path: <PATH TO CHECK>
          requirements: requirements-fmt.txt

**Options**

The following inputs are supported to change the way the Action is performed, and
must be specified as part of the ``with`` section of the job step:

.. attribute:: path (required)

    One or more paths (relative to the repository root) that should be checked.

.. attribute:: requirements

    Path to a requirements file (relative to repo root) that should be installed before
    checking formatting. Any pinned version of black, µsort, or µfmt will be used,
    unless otherwise overridden by :attr:`version`, :attr:`black-version`, or
    :attr:`usort-version`, or incompatible with the version of µfmt requested. 

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
      rev: v2.0.0
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
                - usort == 1.0.4


Visual Studio Code
~~~~~~~~~~~~~~~~~~

µfmt has an official VS Code extension to use µfmt as a formatter for Python files.
Once installed, µfmt can be set as the default formatter with the following settings:

.. code-block:: json

    "[python]": {
      "editor.defaultFormatter": "omnilib.ufmt"
    }

µfmt can automatically format when saving with the following settings:

.. code-block:: json

    "[python]": {
      "editor.defaultFormatter": "omnilib.ufmt",
      "editor.formatOnSave": true
    }

For more details, or to install the extension, see the Visual Studio Marketplace page:

.. image:: https://img.shields.io/badge/VSCode-ufmt-007ACC?style=for-the-badge&logo=visualstudiocode
    :alt: VS Code extension marketplace
    :target: https://marketplace.visualstudio.com/items?itemName=omnilib.ufmt

.. image:: https://img.shields.io/badge/-Install%20Now-107C10?style=for-the-badge&logo=visualstudiocode
    :alt: Install VS Code extension now
    :target: vscode:extension/omnilib.ufmt

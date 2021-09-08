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
API Reference
=============

.. module:: ufmt

When integrating µfmt into an existing toolchain or workflow, it is highly recommended
to use the simple, or high-level, API whenever possible. It is designed to provide easy
mechanisms for customizing configuration and post-processing file content, while
handling the boring parts of formatting large codebases, like file discovery, reading
or writing bytes from disk, or managing workers processes to optimize performance.

**When in doubt,** :func:`ufmt_paths` **should be the go-to method of using µfmt
within other tools.**


Simple API
----------

.. autofunction:: ufmt.ufmt_paths

.. autofunction:: ufmt.ufmt_file

.. autoclass:: ufmt.Result

.. autoclass:: ufmt.BlackConfig

.. autoclass:: ufmt.UsortConfig

.. autoclass:: ufmt.BlackConfigFactory

.. autoclass:: ufmt.UsortConfigFactory

.. autoclass:: ufmt.Processor
    :special-members: __call__

.. autoclass:: ufmt.SkipFormatting


Low-level API
-------------

.. autoclass:: ufmt.Encoding

.. autoclass:: ufmt.FileContent

.. autoclass:: ufmt.Newline

.. autofunction:: ufmt.ufmt_bytes

.. autofunction:: ufmt.ufmt_stdin

.. autofunction:: ufmt.util.normalize_result

.. autofunction:: ufmt.util.read_file

.. autofunction:: ufmt.util.write_file

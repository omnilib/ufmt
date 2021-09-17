# µfmt

Safe, atomic formatting with [black][] and [µsort][]

[![version](https://img.shields.io/pypi/v/ufmt.svg)](https://pypi.org/project/ufmt)
[![documentation](https://readthedocs.org/projects/ufmt/badge/?version=latest)](https://ufmt.omnilib.dev)
[![changelog](https://img.shields.io/badge/change-log-blue)](https://ufmt.omnilib.dev/en/latest/changelog.html)
[![license](https://img.shields.io/pypi/l/ufmt.svg)](https://github.com/omnilib/ufmt/blob/master/LICENSE)
[![build status](https://github.com/omnilib/ufmt/workflows/Build/badge.svg)](https://github.com/omnilib/ufmt/actions)
[![code coverage](https://img.shields.io/codecov/c/gh/omnilib/ufmt)](https://codecov.io/gh/omnilib/ufmt)

µfmt is a safe, atomic code formatter for Python built on top of [black] and [µsort]:

> Black makes code review faster by producing the smallest diffs possible. Blackened code looks the same regardless of the project you’re reading.

> μsort is a safe, minimal import sorter. Its primary goal is to make no “dangerous” changes to code, and to make no changes on code style.

µfmt formats files in-memory, first with µsort and then with black, before writing any
changes back to disk. This enables a combined, atomic step in CI/CD workflows for
checking or formatting files, without any with conflict or intermediate changes between
the import sorter and the code formatter.


Install
-------

µfmt requires Python 3.6 or newer. You can install it from PyPI:

```shell-session
$ pip install ufmt
```

If you want to prevent unexpected formatting changes that can break your CI workflow,
make sure to pin your transitive dependencies–including black, µsort, and µfmt–to your
preferred versions.

If you use `requirements.txt`, this might look like:

```text
black==20.8b1
ufmt==1.2
usort==0.6.3
```


Usage
-----

To format one or more files or directories in place:

```shell-session
$ ufmt format <path> [<path> ...]
```

To validate files are formatted correctly, like for CI workflows:

```shell-session
$ ufmt check <path> [<path> ...]
```

To validate formatting and generate a diff of necessary changes:

```shell-session
$ ufmt diff <path> [<path> ...]
```


[pre-commit] hook
-----------------

µfmt provides a [pre-commit] hook. To format your diff before 
every commit, add the following to your `.pre-commit-config.yaml` file:

```yaml
  - repo: https://github.com/omnilib/ufmt
    rev: 1.3.0
    hooks:
      - id: ufmt
```

You can change the `rev` to any version `>= 1.3.0`. To pin `black` and `usort`, use the 
`additional_dependencies` option:

```yaml
    hooks: 
      - id: ufmt 
        additional_dependencies: 
          - black == 20.8b0 
          - usort == 0.6.3
```


License
-------

µfmt is copyright [John Reese](https://jreese.sh), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.


[black]: https://black.readthedocs.io
[µsort]: https://usort.readthedocs.io
[pre-commit]: https://pre-commit.com
# µfmt

Safe, atomic formatting with [black][] and [µsort][]

[![version](https://img.shields.io/pypi/v/ufmt.svg)](https://pypi.org/project/ufmt)
[![documentation](https://readthedocs.org/projects/ufmt/badge/?version=latest)](https://ufmt.omnilib.dev)
[![changelog](https://img.shields.io/badge/change-log-lightgrey)](https://ufmt.omnilib.dev/en/latest/changelog.html)
[![license](https://img.shields.io/pypi/l/ufmt.svg)](https://github.com/omnilib/ufmt/blob/master/LICENSE)
[![vscode extension](https://img.shields.io/badge/vscode-extension-007ACC?logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=omnilib.ufmt)

µfmt is a safe, atomic code formatter for Python built on top of [black] and [µsort]:

> Black makes code review faster by producing the smallest diffs possible. Blackened code looks the same regardless of the project you’re reading.

> μsort is a safe, minimal import sorter. Its primary goal is to make no “dangerous” changes to code, and to make no changes on code style.

µfmt formats files in-memory, first with µsort and then with black, before writing any
changes back to disk. This enables a combined, atomic step in CI/CD workflows for
checking or formatting files, without any chance of conflict or intermediate changes
between the import sorter and the code formatter.


Install
-------

µfmt requires Python 3.8 or newer. You can install it from PyPI:

```shell-session
$ pip install ufmt
```

If you want to prevent unexpected formatting changes that can break your CI workflow,
make sure to pin your transitive dependencies–including black, µsort, and µfmt–to your
preferred versions.

If you use `requirements.txt`, this might look like:

```text
black==22.6.0
ufmt==2.0.0
usort==1.0.4
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


Integrations
------------

### GitHub Actions

µfmt provides a GitHub Action that can be added to an existing workflow,
or as a separate workflow or job, to enforce proper formatting in pull requests:

```yaml
jobs:
  ufmt:
    runs-on: ubuntu-latest
    steps:
      - uses: omnilib/ufmt@action-v1
        with:
          path: <PATH TO CHECK>
          requirements: requirements-fmt.txt
          python-version: "3.x"
```

See the [user guide](https://ufmt.omnilib.dev/en/latest/guide.html#github-actions) for details.

### pre-commit hook

µfmt provides a [pre-commit][] hook. To format your diff before
every commit, add the following to your `.pre-commit-config.yaml` file:

```yaml
  - repo: https://github.com/omnilib/ufmt
    rev: v2.0.0
    hooks:
      - id: ufmt
        additional_dependencies: 
          - black == 22.6.0
          - usort == 1.0.4
```

See the [user guide](https://ufmt.omnilib.dev/en/latest/guide.html#pre-commit) for details.

### Visual Studio Code

µfmt has an official VS Code extension to use µfmt as a formatter for Python files.
Once installed, µfmt can be set as the default formatter with the following settings:

```json
"[python]": {
  "editor.defaultFormatter": "omnilib.ufmt"
}
```

µfmt can automatically format when saving with the following settings:

```json
"[python]": {
  "editor.defaultFormatter": "omnilib.ufmt",
  "editor.formatOnSave": true
}
```

For more details, or to install the extension, see the Visual Studio Marketplace page:

<a href="https://marketplace.visualstudio.com/items?itemName=omnilib.ufmt"><img alt="VS Code extension marketplace" src="https://img.shields.io/badge/VSCode-ufmt-007ACC?style=for-the-badge&logo=visualstudiocode" /></a>
<a href="vscode:extension/omnilib.ufmt"><img alt="Install VS Code extension now" src="https://img.shields.io/badge/-Install%20Now-107C10?style=for-the-badge&logo=visualstudiocode" /></a>


License
-------

µfmt is copyright [Amethyst Reese](https://noswap.com), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.


[black]: https://black.readthedocs.io
[µsort]: https://usort.readthedocs.io
[pre-commit]: https://pre-commit.com

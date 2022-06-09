µfmt
====

v2.0.0b1
--------

Beta release

- Fix: Handle CRLF newlines correctly in diff output and results (#85)
- Fix: preserve given path when formatting stdin (#77)

```
$ git shortlog -s v2.0.0a4...v2.0.0b1
     6	John Reese
     2	dependabot[bot]
```


v2.0.0a4
--------

Alpha release

- New: allow raising `SkipFormatting` from pre/post processors to skip file (#79)

```
$ git shortlog -s v2.0.0a3...v2.0.0a4
     4	John Reese
```


v2.0.0a3
--------

Alpha release

- New: ufmt_paths now returns a generator yielding results as they complete (#76)
- New: Add return_content flag to API to save before/after bytes on results (#75)
- Fix: export ufmt_stdin and add to API docs
- Fix: correctly pass pre_processor through ufmt_file

```
$ git shortlog -s v2.0.0a2...v2.0.0a3
    10	John Reese
```


v2.0.0a2
--------

Alpha release

- Feature: added pre-processors to match post-processors (#72)
- Feature: support for formatting via stdin (#71)
- Fix: better error handling when formatting files (#68)

```
$ git shortlog -s v2.0.0a1...v2.0.0a2
    15	John Reese
```


v2.0.0a1
--------

Alpha release

- Feature: Refactor of core API for public usage (#66)
- Feature: Support for passing black/usort config factories (#66)
- Feature: Support for passing post-processor functions (#66)
- Docs: New API reference added, covering high- and low-level API
- Deprecated: `ufmt_string` will be removed in v3.0, use `ufmt_bytes`
- Breaking change: `ufmt_file` and `ufmt_paths` require keyword arguments
- Breaking change: Requires µsort >= 1.0

```
$ git shortlog -s v1.3.3...v2.0.0a1
    14	John Reese
```


v1.3.3
------

Maintenance release

- Adds PEP 561 py.typed marker to package
- Exports core API in `__all__` for type checking
- Updated example version pinnings in readme

```
$ git shortlog -s v1.3.2...v1.3.3
    22	John Reese
     6	dependabot[bot]
```


v1.3.2
------

Maintenance release

- Disallow flit-core==3.7.0 in PEP 518 build (#56, pypa/flit#530)

```
$ git shortlog -s v1.3.1...v1.3.2
     4	John Reese
     7	dependabot[bot]
```


v1.3.1
------

Bugfix release

* Fixed formatting for type stubs (#41, #42)
* Fixed pre-commit hook example in readme (#40)
* Updated dependencies

```
$ git shortlog -s v1.3.0...v1.3.1
    11	John Reese
     1	Mathieu Kniewallner
    19	dependabot[bot]
```


v1.3.0
------

Feature release

* Added support for configurable list of excludes to supplement gitignore (#14)
* Added ufmt project-level configuration support in pyproject.toml (#14)
* Read and pass black's config when formatting sources (#11)
* Added pre-commit hook definition for other projects to use (#15)
* Added basic user guide to documentation
* Upgrade to trailrunner 1.1.0

```
$ git shortlog -s v1.2.1...v1.3.0
    14	John Reese
    14	Philip Meier
```


v1.2.1
------

Maintenance release

* Add support for reading and obeying .gitignore in project root (#10)
* Improve performance on large repositories using trailrunner (#10)

```
$ git shortlog -s v1.2...v1.2.1
     4	John Reese
```


v1.2
----

Feature release

* Major performance improvement via multiprocessing (#4, #5)
* Documented suggested method for pinning black/usort (#8)
* Officially mark µfmt as "stable" (#7)

```
$ git shortlog -s v1.1...v1.2
     7	John Reese
     1	Tim Hatch
```


v1.1
----

Feature release

* Added `diff` command to validate and also output unified diff (#2, #3)
* Fixed shortlog for v1.0 in changelog

```
$ git shortlog -s v1.0...v1.1
     3	John Reese
```


v1.0
----

Initial release

* `format` command formats files in place
* `check` command validates existing formatting
* Basic readme and sphinx docs

```
$ git shortlog -s v1.0
    17	John Reese
     1	Tim Hatch
```


µfmt
====

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
$ git shortlog -s 245e1a1d2047842e60a76ebebfcb108d90786c57...v1.0
     1	John Reese
```


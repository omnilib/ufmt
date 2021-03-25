µfmt
====

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


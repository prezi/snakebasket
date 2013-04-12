# snakebasket
===============

## In 50 words or less?

snakebasket is a recursive python package installer that makes multi-package python development a little easier. It's a layer on top of [pip](https://github.com/pypa/pip) that can resolve and install an entire dependency graph with a single command: `sb install`.

## Installation
---
Within your [virtualenv](https://pypi.python.org/pypi/virtualenv) of choice, run:
`curl -ss -L http://href.prezi.com/snakebasket | bash -s`

## Detailed Description

At Prezi, Python applications make up a large portion of our web infrastructure. From our early beginnings, we have grown with Python as our primary language for web projects. We have seen many advantages and pitfalls of both the Python ecosystem and the language itself. To avoid some of the pitfalls, we write internal tools to support our Python development and ensure that we remain productive when working with our fast-growing codebase.

snakebasket is one of those tools.

### What problem does it solve?

For basic applications with few dependencies and a flat structure (packages that don't depend on other packages which then depend on other packages),   `pip install [dependency]` or even `pip install -r list_of_dependencies.txt` works great.

But let's say you're developing a large project with a dependency graph such as this:

![dependency hell](https://github.com/prezi/snakebasket/wiki/dependency_hell.jpg)

Two big issues come up.

1. You will be `pip install`ing all day, levels and levels of dependencies deep.

2. It's up to you to manually patch packages that depend on different versions of a shared dependency.

snakebasket's purpose is to solve these two headaches. Here are the two main things snakebasket **does** (but pip doesn't):

1. Recursively reads requirements from simple `requirements.txt` or old-school `setup.ph` files when `sb install` is run.

2. Decides between conflicting versions and installs the latest one, regardless of where in the dependency tree it can be specified.

And two things snakebasket **doesn't** (but pip does):

1. Support SVN

2. Support Mercurial

git and PyPI packages only at this point.

## How do we use snakebaset at Prezi?

Many of our projects have dependency hierarchies multiple layers deep. When we want to install one for development or a production build, we simply run `sb install -r requirements.txt` from the project's root, and all packages in the hierarchy are installed in minutes.

## Will snakebasket be useful to you?

If you find yourself running `pip install` over and over again, or if you simply want an automatic way to deal with conflicting requirement specifications, snakebasket could save you some pain.

## What's wrong with pip again, exactly?
pip allows exactly one version of a package to be specified in a given environment, and thus expects all packages to depend on that same single version. In this example:

```python
#foo/setup.py
setup(
    name="foo",
    ...
    packages["ReportLab=1.7"]
)
```

```python
#bar/setup.py
setup(
    name="bar",
    ...
    packages["ReportLab=0.9"]
)
```

where foo.py and bar.py are installed in the same environment, pip would break as it only allows one of the versions to exist at a given time, and it has no mechanism to properly decide which to install.

Thus, to use pip by itself is to have to manually keep all versions in sync across an environment. In complex applications with many contributors, this doesn't scale well.

In the above situation, snakebasket picks the latest version, and then it `sb install`s that decision.

You can specify package dependencies in a few ways (including via setup.py above), but the recommended way is to specify the requirements in a simple root-level `requirements.txt` (or `requirements-$POSTFIX.txt`) from which snakebasket automatically reads:

```
#foo/requirements.txt
ReportLab=1.7
```

```
#bar/requirements.txt
ReportLab=0.9
```

**Explicit versions are always recommended.** Regardless of where it is in the hierarchy, the latest specified version of any dependency is the one that will ultimately be installed. If an explicit version is not specified, snakebasket interprets that to mean the latest available version.

### --prefer-pinned-revision

The only situation where the non-latest version could be installed is where one depedency version is implict (not pinned), another (earlier) dependency version is explicit, and the install command is `sb install --prefer-pinned-revision`.

Of course, all of the above *makes a huge assumption on the backwards compatibility of dependencies*. snakebasket currently relies on this assumption.

---

## Contributing

### State of the Project:

1. **Passes all relevant pip unit tests.**
2. **Passes tests for snakebasket-specific functionality**, along with some test stubs that will be fleshed out in the coming weeks.
3. **Depends on a specific version of pip**. It's included automatically and will be bumped to later versions as they are tested.
4. **Currently only supports installing PyPI packages and [git editables]**, dropping pip's support for SVN and Mercurial

### Installing local development repo
---
Because snakebasket includes a particular [pip](https://github.com/pypa/pip) commit as a submodule, use
```bash
$ git clone --recursive git@github.com:prezi/snakebasket.git 
```
to clone both snakebasket and the pip submodule completely.

### Testing

snakebasket's testing suite is comprised primarily of verbaitum pip tests (with some exclusions) and a handful of snakebasket specific tests. In the `tests` directory you'll see:

```
tests/
    - test_*.py
    - test_sb_*.py
```

`test_*.py` are symlinks to their corresponding `pip/tests/test_*.py` in the pip submodule. `test_sb_*.py` are snakebasket specific tests.

The pip tests that are excluded are declared to be so in `tests/excluded_tests.py`

To run snakebasket tests, you must first create a virtualenv
and add the necessary testing packages:
```bash
$ cd snakebasket
$ virtualenv --distribute --no-site-packages -p python2.6 sb-venv
$ . sb-venv/bin/activate
(sb-venv)$ pip install -r requirements-development.txt 
```
To run tests, make sure the virtualenv is active, then execute the
following from the project root:
```bash
(sb-venv)$ cd tests/
(sb-venv)$ python runtests.py
```
Warnings about certificates are expected, pay them no attention:
```
warning: bitbucket.org certificate with fingerprint 24:9c:45:8b:9c:aa:ba:55:4e:01:6d:58:ff:e4:28:7d:2a:14:ae:3b not verified (check hostfingerprints or web.cacerts config setting)
```

Pull requests and issue tickets are welcome!

# License

snakebasket is released under the [MIT License](http://opensource.org/licenses/MIT).
